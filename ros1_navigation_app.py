import rospy
import os
from nav_msgs.msg import OccupancyGrid
from geometry_msgs.msg import PoseWithCovarianceStamped, PoseStamped, Twist
from turtlesim.msg import Pose as TurtleSimPose
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import uvicorn
from threading import Thread
from PIL import Image, ImageDraw, ImageOps
import numpy as np
import tf
import math
import io
import asyncio
import json
from skimage.draw import polygon  # skimage.draw의 polygon 함수 사용

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 또는 특정 도메인을 지정할 수 있습니다.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"WebSocket connection open: {websocket.client}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print(f"WebSocket connection closed: {websocket.client}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        print(f"Broadcasting message to {len(self.active_connections)} connections: {message}")
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

class NavigationServer:
    def __init__(self):
        rospy.init_node('navigation_server', anonymous=True)
        self.map_data = None
        self.robot_pose = None
        self.robot_velocity = None
        self.turtle_pose = None
        self.original_map_data = None
        self.forbidden_zones = []
        rospy.Subscriber('map', OccupancyGrid, self.map_callback)
        rospy.Subscriber('amcl_pose', PoseWithCovarianceStamped, self.pose_callback)
        rospy.Subscriber('cmd_vel', Twist, self.velocity_callback)
        rospy.Subscriber('/turtle1/pose', TurtleSimPose, self.turtle_pose_callback)
        self.pose_publisher = rospy.Publisher('/initialpose', PoseWithCovarianceStamped, queue_size=10)
        self.goal_publisher = rospy.Publisher('/move_base_simple/goal', PoseStamped, queue_size=10)
        self.map_update_publisher = rospy.Publisher('/map', OccupancyGrid, queue_size=10, latch=True)

    def map_callback(self, msg):
        self.map_data = msg
        if self.original_map_data is None:
            self.original_map_data = msg  # 원래 맵 데이터 저장
        rospy.loginfo(f"Map Origin: {msg.info.origin.position.x}, {msg.info.origin.position.y}")
        rospy.loginfo(f"Map Resolution: {msg.info.resolution}")

    def pose_callback(self, msg):
        self.robot_pose = msg

    def velocity_callback(self, msg):
        self.robot_velocity = msg

    def turtle_pose_callback(self, msg):
        self.turtle_pose = msg

    def get_map_info(self):
        if self.map_data:
            map_info = {
                'origin': {
                    'x': self.map_data.info.origin.position.x,
                    'y': self.map_data.info.origin.position.y,
                    'z': self.map_data.info.origin.position.z
                },
                'resolution': self.map_data.info.resolution,
                'width': self.map_data.info.width,
                'height': self.map_data.info.height,
                'map_image': self.save_map_image(self.map_data)  # 이미지 파일 경로 반환
            }
            return map_info
        else:
            return None

    def save_map_image(self, map_data, filename="/tmp/map_with_grid.png"):
        if map_data:
            map_array = np.array(map_data.data).reshape((map_data.info.height, map_data.info.width))
            
            # 새로운 이미지를 생성
            map_image = Image.new('RGB', (map_data.info.width, map_data.info.height))
            draw = ImageDraw.Draw(map_image)
            
            # 픽셀 값에 따라 색상 설정
            for y in range(map_data.info.height):
                for x in range(map_data.info.width):
                    if map_array[y, x] == -1:
                        color = (255, 255, 255)  # 미탐색: 흰색
                    elif map_array[y, x] == 0:
                        color = (200, 200, 200)  # 빈 공간: 회색
                    elif map_array[y, x] == 100:
                        color = (0, 0, 0)  # 벽: 검정색
                    draw.point((x, y), fill=color)
            
            # 이미지를 좌우 반전
            map_image = ImageOps.mirror(map_image)
        
            
            map_image.save(filename)
            return filename
        else:
            return None

    def get_robot_pose(self):
        if self.robot_pose:
            pose = {
                'x': self.robot_pose.pose.pose.position.x,
                'y': self.robot_pose.pose.pose.position.y,
                'z': self.robot_pose.pose.pose.position.z,
                'orientation': {
                    'x': self.robot_pose.pose.pose.orientation.x,
                    'y': self.robot_pose.pose.pose.orientation.y,
                    'z': self.robot_pose.pose.pose.orientation.z,
                    'w': self.robot_pose.pose.pose.orientation.w
                }
            }
            return pose
        else:
            return None

    def get_robot_pose_json(self):
        pose = self.get_robot_pose()
        if pose:
            pose_json = json.dumps(pose)
            return pose_json
        else:
            return json.dumps({"error": "Robot pose not available"})

    def get_robot_velocity(self):
        if self.robot_velocity:
            velocity = {
                'linear': {
                    'x': self.robot_velocity.linear.x,
                    'y': self.robot_velocity.linear.y,
                    'z': self.robot_velocity.linear.z,
                },
                'angular': {
                    'x': self.robot_velocity.angular.x,
                    'y': self.robot_velocity.angular.y,
                    'z': self.robot_velocity.angular.z,
                }
            }
            return velocity
        else:
            return None

    def get_turtle_pose(self):
        if self.turtle_pose:
            pose = {
                'x': self.turtle_pose.x,
                'y': self.turtle_pose.y,
                'theta': self.turtle_pose.theta
            }
            return pose
        else:
            return None

    def get_turtle_pose_json(self):
        pose = self.get_turtle_pose()
        if pose:
            pose_json = json.dumps(pose)
            return pose_json
        else:
            return json.dumps({"error": "Turtle pose not available"})

    def set_initial_pose(self, x, y, theta):
        pose_msg = PoseWithCovarianceStamped()
        pose_msg.header.stamp = rospy.Time.now()
        pose_msg.header.frame_id = "map"
        pose_msg.pose.pose.position.x = x
        pose_msg.pose.pose.position.y = y
        pose_msg.pose.pose.position.z = 0.0

        # 오일러 각도를 쿼터니언으로 변환
        quaternion = tf.transformations.quaternion_from_euler(0, 0, theta)
        pose_msg.pose.pose.orientation.x = quaternion[0]
        pose_msg.pose.pose.orientation.y = quaternion[1]
        pose_msg.pose.pose.orientation.z = quaternion[2]
        pose_msg.pose.pose.orientation.w = quaternion[3]

        rospy.loginfo(f"Setting initial pose: x={x}, y={y}, theta={theta}")
        self.pose_publisher.publish(pose_msg)

    def set_nav_goal(self, x, y, theta):
        goal_msg = PoseStamped()
        goal_msg.header.stamp = rospy.Time.now()
        goal_msg.header.frame_id = "map"
        goal_msg.pose.position.x = x
        goal_msg.pose.position.y = y
        goal_msg.pose.position.z = 0.0

        # 오일러 각도를 쿼터니언으로 변환
        quaternion = tf.transformations.quaternion_from_euler(0, 0, theta)
        goal_msg.pose.orientation.x = quaternion[0]
        goal_msg.pose.orientation.y = quaternion[1]
        goal_msg.pose.orientation.z = quaternion[2]
        goal_msg.pose.orientation.w = quaternion[3]

        rospy.loginfo(f"Setting navigation goal: x={x}, y={y}, theta={theta}")
        self.goal_publisher.publish(goal_msg)

    def set_walls(self, lines):
        self.forbidden_zones = lines
        self.update_obstacles()
        self.publish_updated_map()

    def clear_walls(self):
        self.forbidden_zones = []
        self.map_data = self.original_map_data  # 원래 맵 데이터로 되돌리기
        self.reload_map()
        rospy.loginfo("Cleared all walls and restored original map")

    def update_obstacles(self):
        if self.map_data:
            grid = np.array(self.map_data.data).reshape((self.map_data.info.height, self.map_data.info.width))
            thickness = 1  # 선의 두께 설정

            for line in self.forbidden_zones:
                x1, y1 = self.map_to_grid_coords(line['x1'], line['y1'])
                x2, y2 = self.map_to_grid_coords(line['x2'], line['y2'])

                # 선을 두껍게 그리기 위해 사각형 영역을 생성
                for t in range(-thickness, thickness + 1):
                    rr, cc = polygon([y1 + t, y2 + t, y2 - t, y1 - t], [x1 - t, x2 - t, x2 + t, x1 + t])
                    valid_rr = np.clip(rr, 0, grid.shape[0] - 1)
                    valid_cc = np.clip(cc, 0, grid.shape[1] - 1)
                    grid[valid_rr, valid_cc] = 100

            grid_msg = OccupancyGrid()
            grid_msg.header.stamp = rospy.Time.now()
            grid_msg.header.frame_id = "map"
            grid_msg.info = self.map_data.info
            grid_msg.data = grid.flatten().tolist()

            self.map_data.data = grid_msg.data  # 맵 데이터 업데이트
            self.save_map(self.map_data, filename="/home/seongmin/update_map.pgm")  # 업데이트된 맵 저장
            self.save_map_image(self.map_data, filename="/tmp/update_map_with_grid.png")  # 업데이트된 맵 이미지 저장
            self.publish_updated_map()

            rospy.loginfo("Updated map with new obstacles")

    def map_to_grid_coords(self, x, y):
        gx = int((x - self.map_data.info.origin.position.x) / self.map_data.info.resolution)
        gy = int((y - self.map_data.info.origin.position.y) / self.map_data.info.resolution)
        return gx, gy

    def save_map(self, map_data, filename="/home/seongmin/map.pgm"):
        map_array = np.array(map_data.data).reshape((map_data.info.height, map_data.info.width))
        map_array = 255 - ((map_array + 1) * 127.5 / 100).astype(np.uint8)  # OccupancyGrid 데이터 변환

        with open(filename, 'wb') as f:
            f.write(b'P5\n%d %d\n255\n' % (map_data.info.width, map_data.info.height))
            map_array.tofile(f)

        rospy.loginfo(f"Map saved to {filename}")

    def publish_updated_map(self):
        if self.map_data:
            self.map_update_publisher.publish(self.map_data)
            rospy.loginfo("Published updated map to /map topic")

    def reload_map(self):
        os.system("rosrun map_server map_server /home/seongmin/map.yaml &")
        rospy.loginfo("Reloaded map with updated obstacles")

nav_server = NavigationServer()

class Pose(BaseModel):
    x: float
    y: float
    theta: float  # degrees

class Line(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float

@app.post("/set_pose/")
def set_pose(pose: Pose):
    theta_rad = math.radians(pose.theta)
    nav_server.set_initial_pose(pose.x, pose.y, theta_rad)
    return {"message": "Pose set successfully"}

@app.post("/set_nav_goal/")
def set_nav_goal(pose: Pose):
    theta_rad = math.radians(pose.theta)
    nav_server.set_nav_goal(pose.x, pose.y, theta_rad)
    return {"message": "Navigation goal set successfully"}

@app.post("/set_walls/")
def set_walls(lines: List[Line]):
    nav_server.set_walls([line.dict() for line in lines])
    return {"message": "Walls set successfully"}

@app.post("/clear_walls/")
def clear_walls():
    nav_server.clear_walls()
    return {"message": "Walls cleared successfully"}

@app.get("/get_sim_pose")
def get_sim_pose():
    pose = nav_server.get_turtle_pose()
    if pose:
        return pose
    else:
        raise HTTPException(status_code=404, detail="Turtle pose not available")

@app.get("/map_info")
def map_info():
    map_info = nav_server.get_map_info()
    if map_info:
        return map_info
    else:
        return {"error": "Map data not available"}

@app.get("/map_image")
def map_image():
    map_path = nav_server.save_map_image(nav_server.map_data)
    if map_path:
        with open(map_path, "rb") as f:
            return Response(content=f.read(), media_type="image/png")
    else:
        return {"error": "Map image not available"}

@app.websocket("/ws/robot_data")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            pose_json = nav_server.get_robot_pose_json()
            velocity = nav_server.get_robot_velocity()
            data = {
                'pose': json.loads(pose_json),
                'velocity': velocity
            }
            await manager.send_personal_message(json.dumps(data), websocket)
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.websocket("/ws/notify")
async def notify_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

def ros_spin():
    rospy.spin()

if __name__ == "__main__":
    Thread(target=ros_spin).start()
    uvicorn.run(app, host="0.0.0.0", port=8000)
