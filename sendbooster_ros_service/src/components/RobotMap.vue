<template>
  <div id="app">
    <header>
      <h1>sendbooster agv robot controller system</h1>
    </header>
    <div class="content">
      <div class="map-container">
        <svg
          :viewBox="`0 0 ${mapWidth} ${mapHeight}`"
          class="map-svg"
          ref="mapSvg"
          @mousedown="startDrawing"
          @mousemove="drawRectangle"
          @mouseup="endDrawing"
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
          <rect
            v-for="(rect, index) in rectangles"
            :key="index"
            :x="rect.x"
            :y="rect.y"
            :width="rect.width"
            :height="rect.height"
            fill="none"
            stroke="blue"
            stroke-dasharray="4"
          />
          <rect
            v-if="isDrawing"
            :x="currentRect.x"
            :y="currentRect.y"
            :width="currentRect.width"
            :height="currentRect.height"
            fill="none"
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
            <input type="number" v-model="pose.x" step="0.000000000000001" required />
            <label for="y">Y:</label>
            <input type="number" v-model="pose.y" step="0.000000000000001" required />
            <label for="theta">Theta:</label>
            <input type="number" v-model="pose.theta" step="0.000000000000001" required />
            <button type="submit">Set Pose</button>
          </form>
        </div>
        <div>
          <h2>Rectangles</h2>
          <div v-for="(rect, index) in rectangles" :key="index" class="rectangle-info">
            <details>
              <summary>Rectangle {{ index + 1 }}</summary>
              <form>
                <label for="rect_x">X:</label>
                <input type="number" :value="convertToRobotCoords(rect).x" readonly />
                <label for="rect_y">Y:</label>
                <input type="number" :value="convertToRobotCoords(rect).y" readonly />
                <label for="rect_width">Width:</label>
                <input type="number" :value="convertToRobotCoords(rect).width" readonly />
                <label for="rect_height">Height:</label>
                <input type="number" :value="convertToRobotCoords(rect).height" readonly />
              </form>
            </details>
          </div>
          <button @click="submitRectangles">Submit</button>
          <button @click="removeAllRectangles">Remove All</button>
        </div>
        <div>
          <h2>Set Navigation Goal</h2>
          <form @submit.prevent="setNavGoal">
            <label for="x_goal">X:</label>
            <input type="number" v-model="navGoal.x" step="0.000000000000001" required />
            <label for="y_goal">Y:</label>
            <input type="number" v-model="navGoal.y" step="0.000000000000001" required />
            <label for="theta_goal">Theta:</label>
            <input type="number" v-model="navGoal.theta" step="0.000000000000001" required />
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
      mapImage: '',
      robotPose: null,
      resolution: 0,
      originX: 0,
      originY: 0,
      mapWidth: 0,
      mapHeight: 0,
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
      reconnectInterval: 5000,
      isDrawing: false,
      currentRect: { x: 0, y: 0, width: 0, height: 0 },
      rectangles: []
    };
  },
  computed: {
    robotMarkerX() {
      if (!this.robotPose) return 0.0

      let offsetX = (this.mapWidth * this.resolution) % 1
      if (offsetX > 0) {offsetX = 1 - offsetX}

      const worldX = - this.robotPose.x - this.originX - offsetX
      const imageX = worldX / this.resolution
      return parseFloat(imageX.toFixed(16))
    },
    robotMarkerY() {
      if (!this.robotPose) return 0.0

      let offsetY = (this.mapHeight * this.resolution) % 1
      if (offsetY > 0) {offsetY = 1 - offsetY}

      const worldY = - this.robotPose.y - this.originY - offsetY
      const imageY = this.mapHeight - (worldY / this.resolution)
      return parseFloat(imageY.toFixed(16))
    },
    navGoalMarkerX() {
      if (!this.navGoal) return 0.0

      let offsetX = (this.mapWidth * this.resolution) % 1
      if (offsetX > 0) {offsetX = 1 - offsetX}

      const worldX = - this.navGoal.x - this.originX - offsetX
      const imageX = worldX / this.resolution
      return parseFloat(imageX.toFixed(16))
    },
    navGoalMarkerY() {
      if (!this.navGoal) return 0.0

      let offsetY = (this.mapHeight * this.resolution) % 1
      if (offsetY > 0) {offsetY = 1 - offsetY}

      const worldY = - this.navGoal.y - this.originY - offsetY
      const imageY = this.mapHeight - (worldY / this.resolution)
      return parseFloat(imageY.toFixed(16))
    }
  },
  async created() {
    await this.fetchMapInfo()
    this.connectWebSocket()
    this.connectNotificationWebSocket() // 알림을 위한 웹소켓 연결
  },
  beforeUnmount() {
    if (this.socket) {
      this.socket.close()
    }
    if (this.notificationSocket) {
      this.notificationSocket.close()
    }
  },
  methods: {
    async fetchMapInfo() {
      try {
        const response = await axios.get('http://localhost:8000/map_info')
        const mapData = response.data
        this.mapImage = 'http://localhost:8000/map_image'
        this.resolution = parseFloat(mapData.resolution.toFixed(16))
        this.originX = parseFloat(mapData.origin.x.toFixed(16))
        this.originY = parseFloat(mapData.origin.y.toFixed(16))
        this.mapWidth = mapData.width
        this.mapHeight = mapData.height

        console.log(`Map Info - Origin: (${this.originX}, ${this.originY}), Resolution: ${this.resolution}, Dimensions: (${this.mapWidth}, ${this.mapHeight})`)
      } catch (error) {
        console.error('Error fetching map info:', error)
      }
    },
    connectWebSocket() {
      this.socket = new WebSocket('ws://localhost:8000/ws/robot_data')

      this.socket.onopen = () => {
        console.log('WebSocket connection opened')
      }

      this.socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          this.robotPose = {
            x: parseFloat(data.pose.x.toFixed(16)),
            y: parseFloat(data.pose.y.toFixed(16)),
            z: parseFloat(data.pose.z.toFixed(16)),
            orientation: {
              x: parseFloat(data.pose.orientation.x.toFixed(16)),
              y: parseFloat(data.pose.orientation.y.toFixed(16)),
              z: parseFloat(data.pose.orientation.z.toFixed(16)),
              w: parseFloat(data.pose.orientation.w.toFixed(16))
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
    connectNotificationWebSocket() {
      this.notificationSocket = new WebSocket('ws://localhost:8000/ws/notify')

      this.notificationSocket.onopen = () => {
        console.log('Notification WebSocket connection opened')
      }

      this.notificationSocket.onmessage = (event) => {
        alert(event.data) // 서버에서 받은 메시지를 alert로 표시
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
    startDrawing(event) {
      const svg = this.$refs.mapSvg;
      const pt = svg.createSVGPoint();
      pt.x = event.clientX;
      pt.y = event.clientY;
      const svgP = pt.matrixTransform(svg.getScreenCTM().inverse());

      this.currentRect.x = svgP.x;
      this.currentRect.y = svgP.y;
      this.currentRect.width = 0;
      this.currentRect.height = 0;
      this.isDrawing = true;
    },
    drawRectangle(event) {
      if (!this.isDrawing) return;

      const svg = this.$refs.mapSvg;
      const pt = svg.createSVGPoint();
      pt.x = event.clientX;
      pt.y = event.clientY;
      const svgP = pt.matrixTransform(svg.getScreenCTM().inverse());

      this.currentRect.width = svgP.x - this.currentRect.x;
      this.currentRect.height = svgP.y - this.currentRect.y;
    },
    endDrawing() {
      this.isDrawing = false;
      this.rectangles.push({ ...this.currentRect });
      this.currentRect = { x: 0, y: 0, width: 0, height: 0 };
    },
    setNavGoalByClick(event) {
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
      this.navGoal.x = parseFloat(worldX.toFixed(16));
      this.navGoal.y = parseFloat(worldY.toFixed(16));
      this.goalSet = false; // 클릭 시 goalSet을 false로 설정하여 빨간색 마커 표시

      // 변환된 좌표를 콘솔에 출력합니다.
      console.log(`Mapped coordinates: x=${this.navGoal.x}, y=${this.navGoal.y}`);
    },
    convertToRobotCoords(rect) {
      const worldX = ((this.mapWidth - rect.x) * this.resolution) + this.originX;
      const worldY = (rect.y * this.resolution) + this.originY;
      const width = rect.width * this.resolution;
      const height = rect.height * this.resolution;
      return {
        x: parseFloat(worldX.toFixed(6)),
        y: parseFloat(worldY.toFixed(6)),
        width: parseFloat(width.toFixed(6)),
        height: parseFloat(height.toFixed(6))
      };
    },
    async setPose() {
      try {
        await axios.post('http://localhost:8000/set_pose', this.pose)
        alert('Pose set successfully')
      } catch (error) {
        console.error(error)
        alert('Failed to set pose')
      }
    },
    async setNavGoal() {
      try {
        await axios.post('http://localhost:8000/set_nav_goal', this.navGoal)
        alert('Navigation goal set successfully')
      } catch (error) {
        console.error(error)
        alert('Failed to set navigation goal')
      }
    },
    async submitRectangles() {
      const forbiddenZones = this.rectangles.map(rect => this.convertToRobotCoords(rect));
      try {
        await axios.post('http://localhost:8000/set_forbidden_zones', forbiddenZones);
        alert(`Number of forbidden zones set: ${this.rectangles.length}`);
      } catch (error) {
        console.error(error);
        alert('Failed to set forbidden zones');
      }
    },
    async removeAllRectangles() {
      try {
        await axios.post('http://localhost:8000/clear_forbidden_zones');
        this.rectangles = [];
        alert('All forbidden zones cleared');
      } catch (error) {
        console.error(error);
        alert('Failed to clear forbidden zones');
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

.rectangle-info {
  margin-bottom: 10px;
}
</style>
