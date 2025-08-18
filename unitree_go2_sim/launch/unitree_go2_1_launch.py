import os
import subprocess
import tempfile

import launch_ros
from ament_index_python.packages import get_package_share_directory
from launch_ros.actions import Node

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    GroupAction,
    TimerAction,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution, PythonExpression


def generate_launch_description():
    use_sim_time = LaunchConfiguration("use_sim_time")
    # Fixed namespace for go2_1
    namespace = "go2_1"
    base_frame = "base_link"

    unitree_go2_sim = launch_ros.substitutions.FindPackageShare(
        package="unitree_go2_sim").find("unitree_go2_sim")
    unitree_go2_description = launch_ros.substitutions.FindPackageShare(
        package="unitree_go2_description").find("unitree_go2_description")
    
    joints_config = os.path.join(unitree_go2_sim, "config/joints/joints.yaml")
    # Use combined controller config that includes both go2 and go2_1 controllers
    ros_control_config_go2 = os.path.join(
        unitree_go2_sim, "config/ros_control/ros_control_go2.yaml"
    )
    gait_config = os.path.join(unitree_go2_sim, "config/gait/gait.yaml")
    links_config = os.path.join(unitree_go2_sim, "config/links/links.yaml")
    default_model_path = os.path.join(unitree_go2_description, "urdf/unitree_go2_robot.xacro")
    default_world_path = os.path.join(unitree_go2_description, "worlds/default.sdf")

    declare_use_sim_time = DeclareLaunchArgument(
        "use_sim_time",
        default_value="true",
        description="Use simulation (Gazebo) clock if true",
    )
    # Note: No RViz launch argument - go2_1 uses RViz from main go2 launch
    declare_robot_name = DeclareLaunchArgument(
        "robot_name", default_value="go2_1", description="Robot name"
    )
    declare_lite = DeclareLaunchArgument(
        "lite", default_value="false", description="Lite"
    )
    declare_ros_control_file = DeclareLaunchArgument(
        "ros_control_file",
        default_value=ros_control_config_go2,
        description="Ros control config path",
    )
    declare_gazebo_world = DeclareLaunchArgument(
        "world", default_value=default_world_path, description="Gazebo world name"
    )

    declare_gui = DeclareLaunchArgument(
        "gui", default_value="true", description="Use gui"
    )
    declare_world_init_x = DeclareLaunchArgument("world_init_x", default_value="2.0")  # Different position
    declare_world_init_y = DeclareLaunchArgument("world_init_y", default_value="0.0")
    declare_world_init_z = DeclareLaunchArgument("world_init_z", default_value="0.375")
    declare_world_init_heading = DeclareLaunchArgument(
        "world_init_heading", default_value="0.0"
    )
    declare_description_path = DeclareLaunchArgument(
        "unitree_go2_description_path",
        default_value=default_model_path,
        description="Path to the robot description xacro file",
    )
    
    # Description nodes and parameters  
    robot_description = {"robot_description": Command([
        "xacro ", LaunchConfiguration("unitree_go2_description_path"),
        " namespace:=", namespace,
        " ros_control_config_file:=", ros_control_config_go2
    ])}
    
    # Global robot state publisher for Gazebo (no namespace for robot_description)
    global_robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[
            robot_description,
            {"use_sim_time": use_sim_time},
            {"publish_tf": False}  # Don't publish TF globally
        ],
    )
    
    # Namespaced robot state publisher for TF
    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        namespace=namespace,
        output="screen", 
        parameters=[
            robot_description,
            {"use_sim_time": use_sim_time}
        ],
    )
    
    # CHAMP controller nodes
    quadruped_controller_node = Node(
        package="champ_base",
        executable="quadruped_controller_node",
        namespace=namespace,
        output="screen",
        parameters=[
            {"use_sim_time": use_sim_time},
            {"gazebo": True},
            {"publish_joint_states": True},
            {"publish_joint_control": True},
            {"publish_foot_contacts": False},
            {"joint_controller_topic": "joint_group_effort_controller_go2_1/joint_trajectory"},
            {"urdf": Command(['xacro ', LaunchConfiguration('unitree_go2_description_path')])},
            joints_config,
            links_config,
            gait_config,
            {"hardware_connected": False},
            {"publish_foot_contacts": False},
            {"close_loop_odom": True},
        ],
        remappings=[
            ("/cmd_vel/smooth", f"/{namespace}/cmd_vel")
        ],
    )

    state_estimator_node = Node(
        package="champ_base",
        executable="state_estimation_node",
        namespace=namespace,
        output="screen",
        parameters=[
            {"use_sim_time": use_sim_time},
            {"orientation_from_imu": True},
            {"urdf": Command(['xacro ', LaunchConfiguration('unitree_go2_description_path')])},
            joints_config,
            links_config,
            gait_config,
        ],
    )

    base_to_footprint_ekf = Node(
        package="robot_localization",
        executable="ekf_node",
        name="base_to_footprint_ekf",
        namespace=namespace,
        output="screen",
        parameters=[
            {"base_link_frame": base_frame},
            {"use_sim_time": use_sim_time},
            os.path.join(
                get_package_share_directory("champ_base"),
                "config",
                "ekf",
                "base_to_footprint.yaml",
            ),
        ],
        remappings=[("odometry/filtered", "odom/local")],
    )

    footprint_to_odom_ekf = Node(
        package="robot_localization",
        executable="ekf_node",
        name="footprint_to_odom_ekf",
        namespace=namespace,
        output="screen",
        parameters=[
            {"use_sim_time": use_sim_time},
            {"base_link_frame": f"{namespace}/base_footprint"},
            {"odom_frame": f"{namespace}/odom"},
            {"world_frame": f"{namespace}/odom"},
            {"publish_tf": True},
            {"frequency": 50.0},
            {"two_d_mode": True},
            {"odom0": "odom/raw"},
            {"odom0_config": [False, False, False, False, False, False, True, True, False, False, False, True, False, False, False]},
            {"imu0": "imu/data"},
            {"imu0_config": [False, False, False, False, False, True, False, False, False, False, False, True, False, False, False]},
        ],
        remappings=[("odometry/filtered", "odom")],
    )

    # Go2_1 static frame connection (map -> odom)
    map_to_odom_tf_node = Node(
        package='tf2_ros',
        name='map_to_odom_tf_node_go2_1',
        executable='static_transform_publisher',
        parameters=[{'use_sim_time': use_sim_time}],
        arguments=[
            '--x', '0', '--y', '0', '--z', '0',
            '--roll', '0', '--pitch', '0', '--yaw', '0',
            '--frame-id', 'map', '--child-frame-id', f'{namespace}/odom'
        ],
    )
    
    # Go2_1 URDF connection (base_footprint -> base_link)  
    base_footprint_to_base_link_tf_node = Node(
        package='tf2_ros',
        name='base_footprint_to_base_link_tf_node_go2_1',
        executable='static_transform_publisher',
        parameters=[{'use_sim_time': use_sim_time}],
        arguments=[
            '--x', '0', '--y', '0', '--z', '0',
            '--roll', '0', '--pitch', '0', '--yaw', '0',
            '--frame-id', f'{namespace}/base_footprint',
            '--child-frame-id', f'{namespace}/base_link'
        ],
    )

    # Note: No separate RViz - go2_1 will use the RViz instance from the main go2 launch
    
    # Spawn robot in Gazebo Sim (don't start Gazebo again, assume it's running)
    gazebo_spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=[
            '-name', LaunchConfiguration('robot_name'),
            '-topic', 'robot_description',
            '-x', LaunchConfiguration('world_init_x'),
            '-y', LaunchConfiguration('world_init_y'),
            '-z', LaunchConfiguration('world_init_z'),
            '-Y', LaunchConfiguration('world_init_heading')
        ],
    )
    
    # Bridge ROS 2 topics to Gazebo Sim (sensor topics with go2_1 namespace support)
    sensor_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='sensor_bridge_go2_1',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}],
        arguments=[
            # Sensor topics from Gazebo to ROS
            '/imu/data@sensor_msgs/msg/Imu@gz.msgs.IMU',
            '/joint_states@sensor_msgs/msg/JointState@gz.msgs.Model',
            '/velodyne_points/points@sensor_msgs/msg/PointCloud2@gz.msgs.PointCloudPacked',
            '/unitree_lidar/points@sensor_msgs/msg/PointCloud2@gz.msgs.PointCloudPacked',
            '/odom@nav_msgs/msg/Odometry@gz.msgs.Odometry',
            '/rgb_image@sensor_msgs/msg/Image@gz.msgs.Image',
            
            # Control topics from ROS to Gazebo
            '/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist',
            '/joint_group_effort_controller_go2_1/joint_trajectory@trajectory_msgs/msg/JointTrajectory]gz.msgs.JointTrajectory',
        ],
        remappings=[
            # Remap sensor topics to namespace
            ('/imu/data', f'/{namespace}/imu/data'),
            ('/joint_states', f'/{namespace}/joint_states'),
            ('/velodyne_points/points', f'/{namespace}/velodyne_points/points'),
            ('/unitree_lidar/points', f'/{namespace}/unitree_lidar/points'),
            ('/odom', f'/{namespace}/odom'),
            ('/rgb_image', f'/{namespace}/rgb_image'),
            ('/cmd_vel', f'/{namespace}/cmd_vel'),
            ('/joint_group_effort_controller_go2_1/joint_trajectory', f'/{namespace}/joint_group_effort_controller_go2_1/joint_trajectory'),
        ],
    )
    
    # Use spawner nodes with dedicated go2_1 controller names
    controller_spawner_js = TimerAction(
        period=20.0,  # Wait for Gazebo to fully initialize
        actions=[
            Node(
                package="controller_manager",
                executable="spawner",
                output="screen",
                arguments=[
                    "--controller-manager-timeout", "120",
                    "joint_states_controller_go2_1",
                ],
                parameters=[{"use_sim_time": use_sim_time}],
            )
        ]
    )

    controller_spawner_effort = TimerAction(
        period=30.0,  # Wait 5 seconds after joint_states_controller
        actions=[
            Node(
                package="controller_manager",
                executable="spawner",
                output="screen",
                arguments=[
                    "--controller-manager-timeout", "120",
                    "joint_group_effort_controller_go2_1",
                ],
                parameters=[{"use_sim_time": use_sim_time}],
            )
        ]
    )
    
    # Shell script to manually check controller status 
    controller_status_check = TimerAction(
        period=25.0,  # Check status after controllers should be loaded
        actions=[
            ExecuteProcess(
                cmd=["bash", "-c", "echo 'Checking go2_1 controller status:' && ros2 control list_controllers"],
                output='screen',
            )
        ]
    )
    
    return LaunchDescription(
        [
            # Launch arguments
            declare_use_sim_time,
            declare_robot_name,
            declare_lite,
            declare_ros_control_file,
            declare_gazebo_world,
            declare_gui,
            declare_world_init_x,
            declare_world_init_y,
            declare_world_init_z,
            declare_world_init_heading,
            declare_description_path, 
            
            # Robot nodes (no Gazebo launch - assume it's running)
            global_robot_state_publisher,
            robot_state_publisher_node,
            gazebo_spawn_robot,
            sensor_bridge,
            
            # CHAMP controller nodes
            quadruped_controller_node,
            state_estimator_node,
            
            # EKF nodes for localization
            base_to_footprint_ekf,
            footprint_to_odom_ekf,
            
            # TF publishers for frame connections
            map_to_odom_tf_node,
            base_footprint_to_base_link_tf_node,
            
            # Controller spawners that handle the complete lifecycle
            controller_spawner_js,
            controller_spawner_effort,
            controller_status_check,
            
            # Note: Uses RViz from main go2 launch - no separate visualization
        ]
    )