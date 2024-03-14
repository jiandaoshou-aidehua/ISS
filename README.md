# ISS
智能自动驾驶系统（ISS）是一种用于研究的自动驾驶框架。该代码在 **Ubuntu 20.04** 上进行了测试。

## Installation
参考 [安装](Install/INSTALL.md) 下的一些环境搭建命令。

## Usage
要使用 ROS-Noetic, 首先构建ROS工作空间
```
cd ros1_ws && catkin build
source devel/setup.bash # or setup.zsh
```
打开 CARLA 服务器

```
cd carla-0.9.13
./CarlaUE4.sh
```

启动 ros 节点，为智能驾驶车辆作全局路径规划

```
roslaunch carla_bridge carla_demo.launch 
```
使用 Gazebo
```
roslaunch robot_gazebo gazebo_demo.launch
```
使用 RViz 设置目标点。

## Documentation
Refer [here](https://tis.ios.ac.cn/iss/) for the documentation.

## Conventions
1. This repository utilizes **ROS's right-handed** coordinate system. This is distinct from **CARLA's left-handed** coordinate system. The ``carla_bridge`` node is responsible for handling the necessary conversions between these two coordinate systems.
2. Angles are in -pi to pi.
