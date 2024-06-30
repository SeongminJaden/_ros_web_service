# sentbooster_ros_web_service

API 엔드포인트</br>
/set_pose/: 초기 포즈를 설정합니다.</br>

HTTP 메소드: POST</br>
Body 형식:</br>
json</br>
```
{
    "x": float,
    "y": float,
    "theta": float  // 각도(degrees)
}
```
/set_nav_goal/: 네비게이션 목표 지점을 설정합니다.</br>
HTTP 메소드: POST</br>
Body 형식:</br>
json</br>
```
{
    "x": float,
    "y": float,
    "theta": float  // 각도(degrees)
}
```
/set_walls/: 장애물을 설정합니다.</br>
HTTP 메소드: POST</br>
Body 형식:</br>
json</br>
```
[
    {
        "x1": float,
        "y1": float,
        "x2": float,
        "y2": float
    },
    ...
]
```
/clear_walls/: 장애물을 초기화합니다.</br>
HTTP 메소드: POST</br>
</br>
/get_sim_pose: 시뮬레이션 로봇의 위치를 조회합니다.</br>
HTTP 메소드: GET</br>
</br>
/map_info: 맵 정보를 조회합니다.</br>
HTTP 메소드: GET</br>
</br>
/map_image: 맵 이미지를 조회합니다.</br>
HTTP 메소드: GET</br>

WebSocket 엔드포인트</br>
/ws/robot_data: 로봇의 위치와 속도 데이터를 실시간으로 전달합니다.</br>
형식: JSON</br>
보내는 데이터 예시:</br>
json</br>
```
{
    "pose": {
        "x": float,
        "y": float,
        "z": float,
        "orientation": {
            "x": float,
            "y": float,
            "z": float,
            "w": float
        }
    },
    "velocity": {
        "linear": {
            "x": float,
            "y": float,
            "z": float
        },
        "angular": {
            "x": float,
            "y": float,
            "z": float
        }
    }
}
```
/ws/notify: 알림을 실시간으로 전달합니다.</br>
현재는 주기적으로 연결을 유지하는 용도로 사용됩니다.</br>
