# Multi-Robot Go2 Controller Configuration Guide

This directory contains ROS2 controller configurations for multiple Go2 robots in simulation. Each robot namespace requires its own dedicated controller configuration file and launch file.

## 📁 Current Files

### Controller Configurations
- `ros_control.yaml` - **Default/Fallback** controller config (non-namespaced joints)
- `ros_control_go2.yaml` - **Combined** controller config (includes both go2 and go2_1 controllers)  
- `ros_control_go2_1.yaml` - **Standalone go2_1** controller config (for reference only)

### Launch Files (in `../../../launch/`)
- `unitree_go2_launch.py` - **Main launch file** (supports `go2` namespace + Gazebo startup)
- `unitree_go2_1_launch.py` - **go2_1 dedicated launch file** (assumes Gazebo running)

---

## 🚀 How to Launch Multiple Robots

### 1️⃣ Launch First Robot (go2 with Gazebo)
```bash
ros2 launch unitree_go2_sim unitree_go2_launch.py
```
- **Namespace**: `go2`
- **Robot Name**: `go2`
- **Controller Config**: `ros_control_go2.yaml`
- **Spawns at**: `x=0, y=0`
- **Includes**: Gazebo startup

### 2️⃣ Launch Second Robot (go2_1)
```bash
# In a new terminal (Gazebo must already be running)
ros2 launch unitree_go2_sim unitree_go2_1_launch.py
```
- **Namespace**: `go2_1` 
- **Robot Name**: `go2_1`
- **Controller Config**: `ros_control_go2_1.yaml`
- **Spawns at**: `x=2.0, y=0`
- **Assumes**: Gazebo already running
- **Visualization**: Uses the same RViz instance from go2 launch (both robots visible in one RViz)

---

## ➕ Adding a New Robot (e.g., go2_2)

Follow these steps to add another Go2 robot:

### Step 1: Add Controllers to Main Config

You need to add the new robot's controllers to `ros_control_go2.yaml` (the main config file):

1. **Add controller definitions to the controller_manager section**:
   ```yaml
   controller_manager:
     ros__parameters:
       # ... existing controllers ...
       joint_group_effort_controller_go2_2:
         type: joint_trajectory_controller/JointTrajectoryController
       joint_states_controller_go2_2:
         type: joint_state_broadcaster/JointStateBroadcaster
   ```

2. **Add the full controller configurations at the end of the file**:
   ```yaml
   # go2_2 controller configurations
   joint_group_effort_controller_go2_2:
     ros__parameters:
       # ... full config with go2_2/ prefixed joints ...
   
   joint_states_controller_go2_2:
     ros__parameters:
       use_sim_time: true
   ```

### Step 2: Create Standalone Config (Optional)

Create a standalone config file for reference: `ros_control_go2_2.yaml`

```bash
cp ros_control_go2_1.yaml ros_control_go2_2.yaml
```

Edit the new file and update:

1. **Controller Names** (must be unique):
   ```yaml
   controller_manager:
     ros__parameters:
       joint_group_effort_controller_go2_2:  # Change from go2_1 to go2_2
         type: joint_trajectory_controller/JointTrajectoryController
       joint_states_controller_go2_2:        # Change from go2_1 to go2_2
         type: joint_state_broadcaster/JointStateBroadcaster
   ```

2. **Controller Section Names**:
   ```yaml
   joint_group_effort_controller_go2_2:     # Change from go2_1 to go2_2
     ros__parameters:
       # ... rest of config
   
   joint_states_controller_go2_2:           # Change from go2_1 to go2_2
     ros__parameters:
       # ... rest of config
   ```

3. **Joint Names** (update all joint names):
   ```yaml
   joints:
   - go2_2/lf_hip_joint          # Change from go2_1/ to go2_2/
   - go2_2/lf_upper_leg_joint
   # ... all other joints
   
   gains:
     go2_2/lf_hip_joint:         # Change from go2_1/ to go2_2/
       d: 1.0
       # ... rest of gains config
   ```

### Step 3: Create Launch File

Create a new launch file: `../../../launch/unitree_go2_2_launch.py`

```bash
cp ../../../launch/unitree_go2_1_launch.py ../../../launch/unitree_go2_2_launch.py
```

Edit the new file and update:

1. **Namespace** (line ~26):
   ```python
   namespace = "go2_2"  # Change from go2_1 to go2_2
   ```

2. **Robot Name Default** (line ~49):
   ```python
   declare_robot_name = DeclareLaunchArgument(
       "robot_name", default_value="go2_2", description="Robot name"
   )
   ```

3. **Controller Config Path** (line ~35):
   ```python
   ros_control_config_go2_2 = os.path.join(
       unitree_go2_sim, "config/ros_control/ros_control_go2_2.yaml"
   )
   ```

4. **Spawn Position** (line ~65):
   ```python
   declare_world_init_x = DeclareLaunchArgument("world_init_x", default_value="4.0")  # Different position
   ```

5. **Controller Topic Remapping** (line ~121):
   ```python
   {"joint_controller_topic": "joint_group_effort_controller_go2_2/joint_trajectory"},
   ```

6. **Node Names** (to avoid conflicts):
   ```python
   # Update all node names to be unique
   name='map_to_odom_tf_node_go2_2',        # line ~186
   name='base_footprint_to_base_link_tf_node_go2_2',  # line ~197
   name='sensor_bridge_go2_2',              # line ~235
   ```
   
   **Note**: Remove the RViz node entirely - new robots will share the RViz from the first robot launch.

7. **Controller Spawner Arguments** (lines ~309-324):
   ```python
   arguments=[
       "--controller-manager-timeout", "120",
       "joint_states_controller_go2_2",     # Change from go2_1 to go2_2
   ],
   
   # And for the effort controller:
   arguments=[
       "--controller-manager-timeout", "120", 
       "joint_group_effort_controller_go2_2", # Change from go2_1 to go2_2
   ],
   ```

### Step 4: Build and Launch

```bash
# Build the workspace
colcon build --packages-select unitree_go2_sim

# Source the workspace  
source install/setup.bash

# Launch the new robot (assumes Gazebo is running from go2)
ros2 launch unitree_go2_sim unitree_go2_2_launch.py
```

---

## 🔧 Controller Architecture

### Global Controller Manager
- All robots share the **same global controller manager** (`/controller_manager`)
- **All controllers are defined in the main go2 config file** (`ros_control_go2.yaml`)
- Each robot has **unique controller names** to avoid conflicts
- Example:
  - `go2`: `joint_states_controller`, `joint_group_effort_controller`
  - `go2_1`: `joint_states_controller_go2_1`, `joint_group_effort_controller_go2_1`  
  - `go2_2`: `joint_states_controller_go2_2`, `joint_group_effort_controller_go2_2`

**🚨 Important**: When adding new robots, you must add their controller definitions to `ros_control_go2.yaml` AND restart the first robot (go2) to reload the controller manager configuration.

### Namespaced Joints
- Each robot's joints are prefixed with its namespace:
  - `go2`: `go2/lf_hip_joint`, `go2/rf_hip_joint`, etc.
  - `go2_1`: `go2_1/lf_hip_joint`, `go2_1/rf_hip_joint`, etc.

### Separate TF Trees
- Each robot maintains its own TF tree:
  - `go2`: `go2/base_link`, `go2/odom`, etc.
  - `go2_1`: `go2_1/base_link`, `go2_1/odom`, etc.

---

## 🐛 Troubleshooting

### Controller Not Loading
```bash
# Check if controllers are loaded
ros2 control list_controllers

# Check controller manager services
ros2 service list | grep controller_manager
```

### Joint Names Mismatch
- Ensure joint names in YAML match the namespaced joints in URDF
- Check: `ros2 topic echo /joint_states` to see actual joint names

### TF Issues
```bash
# Check TF tree
ros2 run tf2_tools view_frames

# Verify robot frames exist
ros2 topic echo /tf_static | grep go2_1
```

### Spawn Position Conflicts
- Ensure each robot has different `world_init_x`, `world_init_y` values
- Check robots aren't spawning on top of each other

### RViz Visualization
- All robots share the **same RViz instance** from the first launch
- Both robots should be visible in the same RViz window
- If you don't see the second robot, check the TF tree and topics:
  ```bash
  # Check if both robots are publishing TF
  ros2 topic echo /tf_static | grep -E "(go2|go2_1)"
  
  # Check robot state publisher topics
  ros2 topic list | grep robot_description
  ```

---

## 📝 Quick Reference

| Robot | Namespace | Config File | Launch File | Spawn Position |
|-------|-----------|-------------|-------------|----------------|
| go2 | `go2` | `ros_control_go2.yaml` | `unitree_go2_launch.py` | `x=0, y=0` |
| go2_1 | `go2_1` | `ros_control_go2_1.yaml` | `unitree_go2_1_launch.py` | `x=2.0, y=0` |
| go2_2 | `go2_2` | `ros_control_go2_2.yaml` | `unitree_go2_2_launch.py` | `x=4.0, y=0` |

**🚨 Important**: Always launch the first robot (`go2`) with the main launch file as it includes Gazebo startup!