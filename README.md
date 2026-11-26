# LeRobot Data Collection

SO-101 teleoperation and recording with RGB, depth, and stereo infrared images from two Intel RealSense cameras.

Each camera records four streams:

| Stream | Storage |
| --- | --- |
| RGB | Three-channel color image |
| Depth | 16-bit numerical depth image |
| Left infrared | 8-bit grayscale repeated across three channels |
| Right infrared | 8-bit grayscale repeated across three channels |

The extension adds these streams to LeRobot observations and dataset metadata. It does not provide hardware synchronization between cameras or record IMU measurements and camera calibration parameters.

## Installation

Requirements: Git, Conda, Python 3.12, a calibrated SO-101 leader/follower pair, and two supported RealSense cameras.

Run the following in Windows Anaconda Prompt, from the directory where you want the two repositories:

```bat
conda create -n lerobot-eight-streams python=3.12 -y
conda activate lerobot-eight-streams
git clone https://github.com/ibrahim-atar109/lerobot-data-collection.git
git clone https://github.com/huggingface/lerobot.git lerobot-runtime
git -C lerobot-runtime checkout eb7a54c6ff4983fc86075442bf4fa61503e7b5d1
python lerobot-data-collection/install.py lerobot-runtime --check
python lerobot-data-collection/install.py lerobot-runtime
python -m pip install -e "./lerobot-runtime[feetech,intelrealsense]"
```

The overrides require the LeRobot commit shown above. The installer checks file hashes, refuses to overwrite unexpected modifications, and backs up original files under `lerobot-runtime/.eight-streams-backup`. To restore them, copy the backed-up files to their matching paths in the runtime checkout.

## Configuration

Replace the placeholders in the commands below:

| Placeholder | Value |
| --- | --- |
| `YOUR_FOLLOWER_PORT`, `YOUR_LEADER_PORT` | Serial ports for the two arms, such as `COM4` |
| `YOUR_FOLLOWER_ID`, `YOUR_LEADER_ID` | IDs associated with the arms' calibration files |
| `YOUR_D435I_SERIAL`, `YOUR_D435_SERIAL` | RealSense serial numbers |
| `YOUR_HF_USERNAME/YOUR_DATASET_NAME` | Dataset identifier |
| `YOUR_DATASET_FOLDER` | New absolute output path |
| `YOUR_TASK_DESCRIPTION` | Task performed in each demonstration |

The examples use 640 x 480 images at 15 FPS. Set `use_rgb`, `use_depth`, `use_ir_left`, and `use_ir_right` for each camera. Both IR options default to false; this configuration requires RGB or depth to remain enabled.

## Teleoperation

Displays all eight streams in Rerun without recording a dataset. Press Ctrl+C to stop.

```bat
python -m lerobot.scripts.lerobot_teleoperate --robot.type=so101_follower --robot.port=YOUR_FOLLOWER_PORT --robot.id=YOUR_FOLLOWER_ID --robot.cameras="{d435i: {type: intelrealsense, serial_number_or_name: 'YOUR_D435I_SERIAL', width: 640, height: 480, fps: 15, use_rgb: true, use_depth: true, use_ir_left: true, use_ir_right: true}, d435: {type: intelrealsense, serial_number_or_name: 'YOUR_D435_SERIAL', width: 640, height: 480, fps: 15, use_rgb: true, use_depth: true, use_ir_left: true, use_ir_right: true}}" --teleop.type=so101_leader --teleop.port=YOUR_LEADER_PORT --teleop.id=YOUR_LEADER_ID --display_data=true --fps=15
```

## Recording

Records ten episodes locally. LeRobot creates the output folder, so the specified folder must not already exist.

```bat
lerobot-record --robot.type=so101_follower --robot.port=YOUR_FOLLOWER_PORT --robot.id=YOUR_FOLLOWER_ID --robot.cameras="{d435i: {type: intelrealsense, serial_number_or_name: 'YOUR_D435I_SERIAL', width: 640, height: 480, fps: 15, use_rgb: true, use_depth: true, use_ir_left: true, use_ir_right: true}, d435: {type: intelrealsense, serial_number_or_name: 'YOUR_D435_SERIAL', width: 640, height: 480, fps: 15, use_rgb: true, use_depth: true, use_ir_left: true, use_ir_right: true}}" --teleop.type=so101_leader --teleop.port=YOUR_LEADER_PORT --teleop.id=YOUR_LEADER_ID --display_data=true --dataset.repo_id=YOUR_HF_USERNAME/YOUR_DATASET_NAME --dataset.root="YOUR_DATASET_FOLDER" --dataset.single_task="YOUR_TASK_DESCRIPTION" --dataset.fps=15 --dataset.num_episodes=10 --dataset.episode_time_s=60 --dataset.reset_time_s=10 --dataset.video=false --dataset.private=true --dataset.push_to_hub=false
```

- Recording starts after device setup.
- Right Arrow ends the current episode early. Keep the terminal focused for keyboard input.
- The next episode starts automatically after the reset interval and saving.
- `dataset.num_episodes`, `dataset.episode_time_s`, and `dataset.reset_time_s` control the episode count and time limits.
- `dataset.video=false` stores lossless images, including numerical depth. Allow sufficient disk space for eight image streams.
- `dataset.push_to_hub=false` disables upload.

Wait for saving to finish before closing the recorder. Interrupting it during saving can leave an incomplete episode.

## Tests

Run in the configured environment:

```bat
python lerobot-data-collection/tests/test_eight_stream_capture.py
```

The tests cover SDK stream configuration, follower observations, grayscale IR encoding, and dataset save/reload. They use synthetic data and do not connect to hardware.

## Source files

`overrides/` mirrors the paths of the four modified LeRobot files:

- `camera_realsense.py`: stream configuration, acquisition, and frame buffers.
- `configuration_realsense.py`: left/right IR configuration flags.
- `so_follower.py`: camera observation integration.
- `feature_utils.py`: image feature metadata.

`manifest.json` contains the upstream commit and file checksums. Install the overrides into LeRobot using `install.py`; this repository is not an independently installable LeRobot package.

## License

Apache-2.0. The modified source files derive from [Hugging Face LeRobot](https://github.com/huggingface/lerobot). See LICENSE and NOTICE.
