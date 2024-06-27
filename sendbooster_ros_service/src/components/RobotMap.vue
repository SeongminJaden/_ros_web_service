<template>
  <div class="map-container">
    <svg
      :viewBox="`0 0 ${mapWidth} ${mapHeight}`"
      class="map-svg"
      ref="mapSvg"
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
      <rect width="100%" height="100%" fill="none" stroke="black" stroke-width="2"/>
    </svg>
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
      socket: null,
      reconnectInterval: 5000
    };
  },
  computed: {
    robotMarkerX() {
      if (!this.robotPose) return 0.0;

      let offsetX = (this.mapWidth * this.resolution) % 1;
      if (offsetX > 0) {offsetX = 1 - offsetX};

      const worldX = - this.robotPose.x - this.originX - offsetX;
      const imageX = worldX / this.resolution;
      return parseFloat(imageX.toFixed(2)); // 좌표를 float로 변환하여 반환
    },
    robotMarkerY() {
      if (!this.robotPose) return 0.0;

      let offsetY = (this.mapHeight * this.resolution) % 1;
      if (offsetY > 0) {offsetY = 1 - offsetY};

      const worldY = - this.robotPose.y - this.originY - offsetY;
      const imageY = this.mapHeight - (worldY / this.resolution);
      return parseFloat(imageY.toFixed(2)); // 좌표를 float로 변환하여 반환
    }
  },
  async created() {
    await this.fetchMapInfo();
    this.connectWebSocket();
  },
  beforeUnmount() {
    if (this.socket) {
      this.socket.close();
    }
  },
  methods: {
    async fetchMapInfo() {
      try {
        const response = await axios.get('http://localhost:8000/map_info');
        const mapData = response.data;
        this.mapImage = 'http://localhost:8000/map_image';  // 이미지 파일 경로 설정
        this.resolution = parseFloat(mapData.resolution.toFixed(16)); // 해상도를 float로 변환
        this.originX = parseFloat(mapData.origin.x.toFixed(16)); // 원점 X를 float로 변환
        this.originY = parseFloat(mapData.origin.y.toFixed(16)); // 원점 Y를 float로 변환
        this.mapWidth = mapData.width;
        this.mapHeight = mapData.height;

        console.log(`Map Info - Origin: (${this.originX}, ${this.originY}), Resolution: ${this.resolution}, Dimensions: (${this.mapWidth}, ${this.mapHeight})`);
      } catch (error) {
        console.error('Error fetching map info:', error);
      }
    },
    connectWebSocket() {
      this.socket = new WebSocket('ws://localhost:8000/ws/robot_pose');

      this.socket.onopen = () => {
        console.log('WebSocket connection opened');
      };

      this.socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.robotPose = {
            x: parseFloat(data.x.toFixed(6)), // 로봇 X 좌표를 float로 변환
            y: parseFloat(data.y.toFixed(6)), // 로봇 Y 좌표를 float로 변환
            z: parseFloat(data.z.toFixed(6)), // 로봇 Z 좌표를 float로 변환
            orientation: {
              x: parseFloat(data.orientation.x.toFixed(6)),
              y: parseFloat(data.orientation.y.toFixed(6)),
              z: parseFloat(data.orientation.z.toFixed(6)),
              w: parseFloat(data.orientation.w.toFixed(6))
            }
          };
          console.log(`Received Robot Pose: (${this.robotPose.x}, ${this.robotPose.y})`);
        } catch (error) {
          console.error('Error parsing message:', error);
        }
      };

      this.socket.onclose = () => {
        console.log('WebSocket connection closed');
        setTimeout(this.connectWebSocket, this.reconnectInterval);  // Reconnect after interval
      };

      this.socket.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.socket.close();
      };
    }
  },
};
</script>

<style>
.map-container {
  position: relative;
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
}
.map-svg {
  width: 100%;
  height: auto;
  display: block;
  border: 1px solid black; /* SVG 테두리 설정 */
}
</style>
