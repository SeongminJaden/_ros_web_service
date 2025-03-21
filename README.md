# _ros_web_service
https://github.com/SeongminJaden/agv_urdf_ros2_gazebo

### 이 repo는 AGV ros2 web service 패키지로 vue.js기반 SLAM-navigation이 가능하도록 개발되었습니다.
API엔드포인트 사용방법은 아래와 같습니다.</br>
시뮬레이션은 ROBOTIS사의 turtlebot3 SIM을 기반으로 구현되었습니다.</br>
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
</br>
좌표 변환 공식</br>
SVG 좌표 -> 실제 좌표 변환:</br>
</br>
worldX = ((mapWidth - svgP.x) * resolution) + originX</br>
worldY = (svgP.y * resolution) + originY</br>
실제 좌표 -> SVG 좌표 변환:</br>
</br>
imageX = (-worldX - originX) / resolution</br>
imageY = mapHeight - ((-worldY - originY) / resolution)</br>
주요 API 및 WebSocket 구성</br>
API 엔드포인트:</br>
</br>
/set_pose: 초기 포즈 설정</br>
/set_nav_goal: 네비게이션 목표 설정</br>
/set_walls: 장애물 벽 설정</br>
/clear_walls: 모든 장애물 벽 초기화</br>
/map_info: 맵 정보 조회</br>
/map_image: 맵 이미지 조회</br>
WebSocket:</br>
</br>
ws://localhost:8000/ws/robot_data: 로봇 데이터 실시간 수신</br>
ws://localhost:8000/ws/notify: 알림 실시간 수신</br>
코드code review_vue.js</br>
```
<template>
  <div id="app">
    <header>
      <h1>agv robot controller</h1>
    </header>
    <div class="toolbar">
      <!-- 모드 변경 버튼 -->
      <button @click="setMode('navigation')" :class="{ active: mode === 'navigation' }">Navigation Mode</button>
      <button @click="setMode('wall')" :class="{ active: mode === 'wall' }">Wall Mode</button>
    </div>
    <div class="content">
      <div class="map-container">
        <svg
          :viewBox="`0 0 ${mapWidth} ${mapHeight}`"
          class="map-svg"
          ref="mapSvg"
          @mousedown="startDrawing"
          @mousemove="drawLine"
          @mouseup="endDrawing"
          @click="setNavGoalByClick"
        >
          <defs>
            <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
              <path d="M 20 0 L 0 0 0 20" fill="none" stroke="lightgray" stroke-width="0.5"/>
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
          <image
            :href="mapImage"
            :width="mapWidth"
            :height="mapHeight"
            x="0"
            y="0"
          />
          <circle
            v-if="robotPose"
            :cx="robotMarkerX"
            :cy="robotMarkerY"
            r="3"
            fill="green"
          />
          <circle
            v-if="navGoal.x !== 0 || navGoal.y !== 0"
            :cx="navGoalMarkerX"
            :cy="navGoalMarkerY"
            r="3"
            fill="red"
          />
          <line
            v-for="(line, index) in lines"
            :key="index"
            :x1="line.x1"
            :y1="line.y1"
            :x2="line.x2"
            :y2="line.y2"
            stroke="blue"
            stroke-dasharray="4"
          />
          <line
            v-if="isDrawing"
            :x1="currentLine.x1"
            :y1="currentLine.y1"
            :x2="currentLine.x2"
            :y2="currentLine.y2"
            stroke="blue"
            stroke-dasharray="4"
          />
          <rect width="100%" height="100%" fill="none" stroke="black" stroke-width="2"/>
        </svg>
      </div>
      <div class="controls">
        <div>
          <h2>Current Robot Velocity</h2>
          <p>Linear Velocity: {{ velocity.linear.x.toFixed(2) }} m/s</p>
          <p>Angular Velocity: {{ velocity.angular.z.toFixed(2) }} rad/s</p>
        </div>
        <div>
          <h2>Set 2D Pose Estimate</h2>
          <form @submit.prevent="setPose">
            <label for="x">X:</label>
            <input type="number" v-model="pose.x" step="0.00001" required />
            <label for="y">Y:</label>
            <input type="number" v-model="pose.y" step="0.00001" required />
            <label for="theta">Theta:</label>
            <input type="number" v-model="pose.theta" step="0.00001" required />
            <button type="submit">Set Pose</button>
          </form>
        </div>
        <div>
          <h2>Lines</h2>
          <div v-for="(line, index) in lines" :key="index" class="line-info">
            <details>
              <summary>Line {{ index + 1 }}</summary>
              <form>
                <label for="line_x1">X1:</label>
                <input type="number" :value="convertToRobotCoords(line).x1" readonly />
                <label for="line_y1">Y1:</label>
                <input type="number" :value="convertToRobotCoords(line).y1" readonly />
                <label for="line_x2">X2:</label>
                <input type="number" :value="convertToRobotCoords(line).x2" readonly />
                <label for="line_y2">Y2:</label>
                <input type="number" :value="convertToRobotCoords(line).y2" readonly />
              </form>
            </details>
          </div>
          <button @click="submitLines">Submit</button>
          <button @click="removeAllLines">Remove All</button>
        </div>
        <div>
          <h2>Set Navigation Goal</h2>
          <form @submit.prevent="setNavGoal">
            <label for="x_goal">X:</label>
            <input type="number" v-model="navGoal.x" step="0.00001" required />
            <label for="y_goal">Y:</label>
            <input type="number" v-model="navGoal.y" step="0.00001" required />
            <label for="theta_goal">Theta:</label>
            <input type="number" v-model="navGoal.theta" step="0.00001" required />
            <button type="submit">Set Nav Goal</button>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  data() {
    return {
      mapImage: '',  // 맵 이미지 URL
      robotPose: null,  // 로봇의 현재 위치
      resolution: 0,  // 맵 해상도
      originX: 0,  // 맵의 X 원점
      originY: 0,  // 맵의 Y 원점
      mapWidth: 0,  // 맵의 너비
      mapHeight: 0,  // 맵의 높이
      velocity: {
        linear: { x: 0 },
        angular: { z: 0 }
      },
      pose: {
        x: 0,
        y: 0,
        theta: 0
      },
      navGoal: {
        x: 0,
        y: 0,
        theta: 0
      },
      socket: null,
      notificationSocket: null,
      reconnectInterval: 5000,  // WebSocket 재연결 간격
      isDrawing: false,  // 드로잉 상태
      currentLine: { x1: 0, y1: 0, x2: 0, y2: 0 },
      lines: [],
      mode: 'navigation'  // 현재 모드
    };
  },
  computed: {
    // 로봇 마커의 X 좌표
    robotMarkerX() {
      if (!this.robotPose) return 0.0

      let offsetX = (this.mapWidth * this.resolution) % 1
      if (offsetX > 0) {offsetX = 1 - offsetX}

      const worldX = - this.robotPose.x - this.originX - offsetX
      const imageX = worldX / this.resolution
      return parseFloat(imageX.toFixed(5))
    },
    // 로봇 마커의 Y 좌표
    robotMarkerY() {
      if (!this.robotPose) return 0.0

      let offsetY = (this.mapHeight * this.resolution) % 1
      if (offsetY > 0) {offsetY = 1 - offsetY}

      const worldY = - this.robotPose.y - this.originY - offsetY
      const imageY = this.mapHeight - (worldY / this.resolution)
      return parseFloat(imageY.toFixed(5))
    },
    // 네비게이션 목표 마커의 X 좌표
    navGoalMarkerX() {
      if (!this.navGoal) return 0.0

      let offsetX = (this.mapWidth * this.resolution) % 1
      if (offsetX > 0) {offsetX = 1 - offsetX}

      const worldX = - this.navGoal.x - this.originX - offsetX
      const imageX = worldX / this.resolution
      return parseFloat(imageX.toFixed(5))
    },
    // 네비게이션 목표 마커의 Y 좌표
    navGoalMarkerY() {
      if (!this.navGoal) return 0.0

      let offsetY = (this.mapHeight * this.resolution) % 1
      if (offsetY > 0) {offsetY = 1 - offsetY}

      const worldY = - this.navGoal.y - this.originY - offsetY
      const imageY = this.mapHeight - (worldY / this.resolution)
      return parseFloat(imageY.toFixed(5))
    }
  },
  async created() {
    await this.fetchMapInfo()  // 맵 정보 가져오기
    this.connectWebSocket()  // 로봇 데이터 WebSocket 연결
    this.connectNotificationWebSocket()  // 알림 WebSocket 연결
  },
  beforeUnmount() {
    if (this.socket) {
      this.socket.close()  // 컴포넌트 언마운트 시 WebSocket 닫기
    }
    if (this.notificationSocket) {
      this.notificationSocket.close()
    }
  },
  methods: {
    // 모드 변경
    setMode(newMode) {
      this.mode = newMode
    },
    // 맵 정보 가져오기
    async fetchMapInfo() {
      try {
        const response = await axios.get('http://localhost:8000/map_info')
        const mapData = response.data
        this.mapImage = 'http://localhost:8000/map_image'
        this.resolution = parseFloat(mapData.resolution.toFixed(5))
        this.originX = parseFloat(mapData.origin.x.toFixed(5))
        this.originY = parseFloat(mapData.origin.y.toFixed(5))
        this.mapWidth = mapData.width
        this.mapHeight = mapData.height

        console.log(`Map Info - Origin: (${this.originX}, ${this.originY}), Resolution: ${this.resolution}, Dimensions: (${this.mapWidth}, ${this.mapHeight})`)
      } catch (error) {
        console.error('Error fetching map info:', error)
      }
    },
    // 로봇 데이터 WebSocket 연결
    connectWebSocket() {
      this.socket = new WebSocket('ws://localhost:8000/ws/robot_data')

      this.socket.onopen = () => {
        console.log('WebSocket connection opened')
      }

      this.socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          this.robotPose = {
            x: parseFloat(data.pose.x.toFixed(5)),
            y: parseFloat(data.pose.y.toFixed(5)),
            z: parseFloat(data.pose.z.toFixed(5)),
            orientation: {
              x: parseFloat(data.pose.orientation.x.toFixed(5)),
              y: parseFloat(data.pose.orientation.y.toFixed(5)),
              z: parseFloat(data.pose.orientation.z.toFixed(5)),
              w: parseFloat(data.pose.orientation.w.toFixed(5))
            }
          }
          this.velocity = data.velocity || this.velocity
          console.log(`Received Robot Pose: (${this.robotPose.x}, ${this.robotPose.y})`)
        } catch (error) {
          console.error('Error parsing message:', error)
        }
      }

      this.socket.onclose = () => {
        console.log('WebSocket connection closed')
        setTimeout(this.connectWebSocket, this.reconnectInterval)
      }

      this.socket.onerror = (error) => {
        console.error('WebSocket error:', error)
        this.socket.close()
      }
    },
    // 알림 WebSocket 연결
    connectNotificationWebSocket() {
      this.notificationSocket = new WebSocket('ws://localhost:8000/ws/notify')

      this.notificationSocket.onopen = () => {
        console.log('Notification WebSocket connection opened')
      }

      this.notificationSocket.onmessage = (event) => {
        alert(event.data)  // 서버에서 받은 메시지를 alert로 표시
      }

      this.notificationSocket.onclose = () => {
        console.log('Notification WebSocket connection closed')
        setTimeout(this.connectNotificationWebSocket, this.reconnectInterval)
      }

      this.notificationSocket.onerror = (error) => {
        console.error('Notification WebSocket error:', error)
        this.notificationSocket.close()
      }
    },
    // 드로잉 시작
    startDrawing(event) {
      if (this.mode !== 'wall') return

      const svg = this.$refs.mapSvg;
      const pt = svg.createSVGPoint();
      pt.x = event.clientX;
      pt.y = event.clientY;
      const svgP = pt.matrixTransform(svg.getScreenCTM().inverse());

      this.currentLine.x1 = svgP.x;
      this.currentLine.y1 = svgP.y;
      this.currentLine.x2 = svgP.x;
      this.currentLine.y2 = svgP.y;
      this.isDrawing = true;
    },
    // 드로잉 중
    drawLine(event) {
      if (!this.isDrawing) return;

      const svg = this.$refs.mapSvg;
      const pt = svg.createSVGPoint();
      pt.x = event.clientX;
      pt.y = event.clientY;
      const svgP = pt.matrixTransform(svg.getScreenCTM().inverse());

      this.currentLine.x2 = svgP.x;
      this.currentLine.y2 = svgP.y;
    },
    // 드로잉 종료
    endDrawing() {
      if (!this.isDrawing) return

      this.isDrawing = false;
      this.lines.push({ ...this.currentLine });
      this.currentLine = { x1: 0, y1: 0, x2: 0, y2: 0 };
    },
    // 네비게이션 목표 설정
    setNavGoalByClick(event) {
      if (this.mode !== 'navigation') return

      const svg = this.$refs.mapSvg; // SVG 요소 참조
      const pt = svg.createSVGPoint(); // SVG 포인트 객체 생성

      pt.x = event.clientX;
      pt.y = event.clientY;

      // 클릭한 좌표를 SVG 내부 좌표로 변환
      const svgP = pt.matrixTransform(svg.getScreenCTM().inverse());

      // 변환된 좌표를 콘솔에 출력합니다.
      console.log(`Transformed coordinates: x=${svgP.x}, y=${svgP.y}`);

      // 맵의 크기를 콘솔에 출력합니다.
      console.log(`Map Width: ${this.mapWidth}px, Map Height: ${this.mapHeight}px`);

      // resolution 값을 사용하여 SVG 좌표를 실제 좌표로 변환
      const worldX = ((this.mapWidth - svgP.x) * this.resolution) + this.originX;
      const worldY = (svgP.y * this.resolution) + this.originY;

      // 변환된 좌표를 navGoal에 설정
      this.navGoal.x = parseFloat(worldX.toFixed(5));
      this.navGoal.y = parseFloat(worldY.toFixed(5));
      this.goalSet = false; // 클릭 시 goalSet을 false로 설정하여 빨간색 마커 표시

      // 변환된 좌표를 콘솔에 출력합니다.
      console.log(`Mapped coordinates: x=${this.navGoal.x}, y=${this.navGoal.y}`);
    },
    // SVG 좌표를 실제 로봇 좌표로 변환
    convertToRobotCoords(line) {
      const worldX1 = ((this.mapWidth - line.x1) * this.resolution) + this.originX;
      const worldY1 = (line.y1 * this.resolution) + this.originY;
      const worldX2 = ((this.mapWidth - line.x2) * this.resolution) + this.originX;
      const worldY2 = (line.y2 * this.resolution) + this.originY;
      return {
        x1: parseFloat(worldX1.toFixed(5)),
        y1: parseFloat(worldY1.toFixed(5)),
        x2: parseFloat(worldX2.toFixed(5)),
        y2: parseFloat(worldY2.toFixed(5))
      };
    },
    // 초기 포즈 설정 API 호출
    async setPose() {
      try {
        await axios.post('http://localhost:8000/set_pose', this.pose)
        alert('Pose set successfully')
      } catch (error) {
        console.error(error)
        alert('Failed to set pose')
      }
    },
    // 네비게이션 목표 설정 API 호출
    async setNavGoal() {
      try {
        await axios.post('http://localhost:8000/set_nav_goal', this.navGoal)
        alert('Navigation goal set successfully')
      } catch (error) {
        console.error(error)
        alert('Failed to set navigation goal')
      }
    },
    // 장애물 벽 설정 API 호출
    async submitLines() {
      const lines = this.lines.map(line => this.convertToRobotCoords(line));
      console.log(lines.length)
      if (lines.length > 0) {
        try {
          await axios.post('http://localhost:8000/set_walls', lines);
          alert(`Number of walls set: ${this.lines.length}`);
        } catch (error) {
          console.error(error);
          alert('Failed to set walls');
        }
      } else {
        alert("Set obstacles first")
      }
    },
    // 모든 장애물 벽 제거 API 호출
    async removeAllLines() {
      try {
        await axios.post('http://localhost:8000/clear_walls');
        this.lines = [];
        alert('All walls cleared');
      } catch (error) {
        console.error(error);
        alert('Failed to clear walls');
      }
    }
  }
}
</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  margin-top: 60px;
}

header {
  text-align: center;
  margin-bottom: 20px;
}

.toolbar {
  text-align: center;
  margin-bottom: 20px;
}

.toolbar button {
  margin: 0 10px;
  padding: 10px 20px;
}

.toolbar button.active {
  background-color: #42b983;
  color: white;
}

.content {
  display: flex;
  justify-content: flex-start; /* 왼쪽에서 정렬 */
  align-items: flex-start; /* 위에서 정렬 */
}

.map-container {
  flex: 1;
  max-width: 50%; /* 전체 너비의 50% */
  margin-right: 20px;
}

.controls {
  flex: 1;
  max-width: 50%; /* 전체 너비의 50% */
}

.map-svg {
  width: 100%;
  height: auto;
  display: block;
  border: 1px solid black;
}

form {
  margin: 20px 0;
}

label {
  margin-right: 10px;
}

input {
  margin-right: 10px;
}

button {
  margin-top: 10px;
}

.line-info {
  margin-bottom: 10px;
}
</style>
```
