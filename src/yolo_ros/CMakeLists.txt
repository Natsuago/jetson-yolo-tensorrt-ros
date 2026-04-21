cmake_minimum_required(VERSION 3.0.2)
project(yolo_ros)

find_package(catkin REQUIRED COMPONENTS
  rospy
  sensor_msgs
  std_msgs
  vision_msgs
  cv_bridge
  image_transport
)

catkin_python_setup()

catkin_package()

catkin_install_python(PROGRAMS
  scripts/detect_node.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(DIRECTORY launch config
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)

