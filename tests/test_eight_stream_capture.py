"""Offline regression tests for RGB/depth/stereo-IR capture; no hardware opens."""
import tempfile
import unittest
from pathlib import Path
from threading import Event
from unittest.mock import Mock, patch

import numpy as np
from PIL import Image

from lerobot.cameras.realsense.camera_realsense import RealSenseCamera
from lerobot.cameras.realsense.configuration_realsense import RealSenseCameraConfig
from lerobot.datasets.image_writer import write_image
from lerobot.utils.errors import DeviceNotConnectedError
from lerobot.utils.feature_utils import hw_to_dataset_features


def camera(**kwargs):
    return RealSenseCamera(RealSenseCameraConfig(
        serial_number_or_name='000000000001', width=8, height=6, fps=15,
        use_depth=True, use_ir_left=True, use_ir_right=True, **kwargs,
    ))


class CaptureTests(unittest.TestCase):
    def test_sdk_requests(self):
        cam = camera()
        cfg = Mock()
        with patch('lerobot.cameras.realsense.camera_realsense.rs.config.enable_device'):
            cam._configure_rs_pipeline_config(cfg)
        calls = cfg.enable_stream.call_args_list
        self.assertEqual(len(calls), 4)
        self.assertEqual([calls[2].args[1], calls[3].args[1]], [1, 2])

    def test_frameset_and_storage(self):
        cam = camera()
        rgb = np.full((6, 8, 3), 17, np.uint8)
        depth = np.full((6, 8), 432, np.uint16)
        left = np.arange(48, dtype=np.uint8).reshape(6, 8)
        right = 255 - left
        frames = Mock()
        frames.get_color_frame.return_value.get_data.return_value = rgb
        frames.get_depth_frame.return_value.get_data.return_value = depth
        frames.get_infrared_frame.side_effect = lambda i: Mock(get_data=lambda: left if i == 1 else right)
        cam.stop_event = Event()
        cam._read_from_hardware = Mock(side_effect=[frames, DeviceNotConnectedError('end test')])
        cam._read_loop()
        # Borrowed SDK buffers must not mutate the published RGB/depth snapshot.
        rgb[:] = 0
        depth[:] = 0
        cam.rs_profile = object()
        cam.rs_pipeline = object()
        cam.thread = Mock(is_alive=lambda: True)
        bundle = cam.read_latest_frames()
        self.assertEqual(set(bundle), {'rgb', 'depth', 'ir_left', 'ir_right'})
        self.assertTrue((bundle['rgb'] == 17).all())
        self.assertTrue((bundle['depth'] == 432).all())
        with tempfile.TemporaryDirectory() as tmp:
            for name, original in [('ir_left', left), ('ir_right', right)]:
                for channel in range(3):
                    np.testing.assert_array_equal(bundle[name][..., channel], original)
                path = Path(tmp) / (name + '.png')
                write_image(bundle[name], path)
                np.testing.assert_array_equal(np.asarray(Image.open(path))[..., 0], original)
            path = Path(tmp) / 'depth.tiff'
            write_image(bundle['depth'], path)
            self.assertTrue((np.asarray(Image.open(path)) == 432).all())
        cam.latest_ir_frames.pop('ir_right')
        with self.assertRaises(RuntimeError):
            cam.read_latest_frames()
        cam.thread = None
        cam.rs_pipeline = None
        cam.rs_profile = None

    def test_eight_features_and_robot_observation(self):
        from lerobot.robots.so_follower.so_follower import SOFollower
        cams = {'d435i': camera(), 'd435': camera()}
        robot = object.__new__(SOFollower)
        robot.id = 'offline_test'
        robot.cameras = cams
        shapes = robot._cameras_ft
        self.assertEqual(len(shapes), 8)
        features = hw_to_dataset_features(shapes, 'observation', use_video=False)
        self.assertEqual(sum(f['info']['is_depth_map'] for f in features.values()), 2)
        self.assertEqual(sum(f['info'].get('is_infrared', False) for f in features.values()), 4)
        self.assertTrue(all(f['dtype'] == 'image' for f in features.values()))

        # Exercise the SO-101 branch without constructing or opening a motor bus.
        from types import SimpleNamespace
        from unittest.mock import PropertyMock
        robot.bus = Mock(is_connected=True)
        robot.bus.sync_read.return_value = {'joint': 0.}
        robot.config = SimpleNamespace(num_read_retries=2)
        for cam in cams.values():
            cam.read_latest_frames = Mock(return_value={
                'rgb': np.zeros((6, 8, 3), np.uint8),
                'depth': np.zeros((6, 8, 1), np.uint16),
                'ir_left': np.zeros((6, 8, 3), np.uint8),
                'ir_right': np.zeros((6, 8, 3), np.uint8),
            })
        with patch.object(RealSenseCamera, 'is_connected', new_callable=PropertyMock, return_value=True):
            observation = robot.get_observation()
        self.assertEqual(set(observation) - {'joint.pos'}, set(shapes))
        for cam in cams.values():
            cam.read_latest_frames.assert_called_once()

    def test_no_ir_default(self):
        cfg = RealSenseCameraConfig(serial_number_or_name='000000000001', width=8, height=6, fps=15)
        self.assertFalse(cfg.use_ir_left)
        self.assertFalse(cfg.use_ir_right)

    def test_dataset_save_and_reload(self):
        from lerobot.datasets.lerobot_dataset import LeRobotDataset
        shapes = {'joint': float}
        for cam in ('d435i', 'd435'):
            for suffix in ('', '_ir_left', '_ir_right'):
                shapes[cam + suffix] = (6, 8, 3)
            shapes[cam + '_depth'] = (6, 8, 1)
        features = hw_to_dataset_features(shapes, 'observation', use_video=False)
        features.update(hw_to_dataset_features({'joint': float}, 'action', use_video=False))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'dataset'
            ds = LeRobotDataset.create('local/eight_stream_test', fps=15, root=root,
                                       features=features, use_videos=False)
            for _ in range(2):
                frame = {'observation.state': np.array([0.], np.float32),
                         'action': np.array([0.], np.float32), 'task': 'test'}
                for key, spec in features.items():
                    if spec['dtype'] == 'image':
                        depth = spec['info']['is_depth_map']
                        frame[key] = np.full(spec['shape'], 432 if depth else 37,
                                             np.uint16 if depth else np.uint8)
                ds.add_frame(frame)
            ds.save_episode()
            ds.finalize()
            loaded = LeRobotDataset('local/eight_stream_test', root=root)
            sample = loaded[0]
            for key, spec in features.items():
                if spec['dtype'] == 'image':
                    expected = 432. if spec['info']['is_depth_map'] else 37. / 255.
                    np.testing.assert_allclose(sample[key].numpy(), expected, atol=1e-6)
            self.assertEqual(len(loaded.meta.camera_keys), 8)
            self.assertEqual(len(loaded.meta.depth_keys), 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)

