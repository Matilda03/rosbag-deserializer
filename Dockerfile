FROM osrf/ros:humble-desktop-full-jammy

WORKDIR /workspace

RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-colcon-common-extensions \
    python3-rosdep \
    ros-humble-autoware-msgs \
    ros-humble-ublox-msgs \
    ros-humble-ublox \
    ros-humble-velodyne-msgs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /ros2_ws

# Build the workspace (optional, if you have sources)
# RUN . /opt/ros/humble/setup.sh && \
#     rosdep update && rosdep install -y --from-paths src --ignore-src --rosdistro humble && \
#     colcon build --symlink-install

ENTRYPOINT ["/bin/bash", "-c", "source /opt/ros/humble/setup.bash && exec bash"]
