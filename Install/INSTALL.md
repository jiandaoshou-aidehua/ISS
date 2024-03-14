# Installation

- 安装 [ROS Noetic](http://wiki.ros.org/noetic/Installation), 以及下载相关依赖:
```
执行 rosrun turtlesim turtlesim_node 出现小乌龟界面，则表示ros安装成功
sudo apt-get install ros-noetic-navigation ros-noetic-gmapping ros-noetic-teb-local-planner ros-noetic-ackermann-msgs ros-noetic-gazebo-ros-pkgs ros-noetic-gazebo-ros-control ros-noetic-joint-state-publisher-gui ros-noetic-ros-control ros-noetic-ros-controllers
```
- 安装 [CARLA 0.9.13](https://github.com/carla-simulator/carla/releases/tag/0.9.13/) 并设置环境变量:
```
export CARLA_ROOT=</path/to/carla>
export PYTHONPATH=$PYTHONPATH:${CARLA_ROOT}/PythonAPI/carla

注意
运行代码时需要 agents 模块， 在 conda 环境 ISS 目录下，还需要配置环境变量
export PYTHONPATH=$PYTHONPATH:/home/.../carla-0.9.13/carla:/home/.../carla-0.9.13/PythonAPI/carla/agents
```
- Create a virtual environment for this repository:
```
conda create -n iss python=3.8
conda activate iss
注意
若要退出当前conda环境，执行
conda deactivate
```
- 安装 [git-lfs](https://git-lfs.github.com/)
- 递归克隆项目及其子模块:
```
git clone --recurse-submodules https://github.com/CAS-LRJ/ISS.git && cd ISS
pip3 install -r Install/requirements.txt
python3 Install/setup.py develop
```
- 安装 PyTorch 和 torch-scatter:
```
pip3 install torch==1.7.1+cu110 torchvision==0.8.2+cu110 torchaudio==0.7.2 -f https://download.pytorch.org/whl/torch_stable.html
pip3 install Install/torch_scatter-2.0.7-cp38-cp38-linux_x86_64.whl
```
- 安装 [CUDA Toolkit 11.8](https://developer.nvidia.com/cuda-11-8-0-download-archive)
- 安装 [MMDetection](https://mmdetection.readthedocs.io/en/latest/get_started.html)
