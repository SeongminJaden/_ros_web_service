<template>
    <div
      class="rectangle-map"
      @mousemove="updateCoordinates"
      @mouseleave="clearCoordinates"
    >
      <div v-html="svgContent" class="floorplan" @click="handleClick"></div>
      <svg class="markers" viewBox="0 0 1000 500">
        <circle
          v-if="point"
          :cx="point.x"
          :cy="500 - point.y"
          r="5"
          fill="red"
        />
      </svg>
      <div class="coordinates" v-if="coordinates">
        ({{ coordinates.x.toFixed(1) }}, {{ coordinates.y.toFixed(1) }})
      </div>
      <div v-if="selectedRoom" class="info">
        <p>Selected Room: {{ selectedRoom }}</p>
      </div>
    </div>
  </template>
  
  <script>
  import axios from 'axios';
  import { io } from 'socket.io-client';
  
  export default {
    data() {
      return {
        svgContent: '',
        coordinates: null,
        selectedRoom: null,
        point: null, // Change to single object
        socket: null,
      };
    },
    methods: {
      async loadSvg() {
        try {
          const response = await axios.get('/assets/floorplan.svg');
          this.svgContent = response.data;
        } catch (error) {
          console.error('Error loading SVG:', error);
        }
      },
      async fetchCoordinates() {
        try {
          const response = await axios.get('http://localhost:3000/coordinates');
          if (response.data.length > 0) {
            this.point = response.data[0];
          }
        } catch (error) {
          console.error('Error fetching coordinates:', error);
        }
      },
      updateCoordinates(event) {
        const rect = event.target.getBoundingClientRect();
        const x = ((event.clientX - rect.left) / rect.width) * 1000;
        const y = 500 - ((event.clientY - rect.top) / rect.height) * 500;
        this.coordinates = { x, y };
      },
      clearCoordinates() {
        this.coordinates = null;
      },
      handleClick(event) {
        if (event.target.classList.contains('room')) {
          const roomId = event.target.id;
          this.selectedRoom = roomId ? `Room ${roomId.replace('room', '')}` : 'Unknown';
          alert(`Coordinates: (${this.coordinates.x.toFixed(1)}, ${this.coordinates.y.toFixed(1)})\nSelected Room: ${this.selectedRoom}`);
        }
      },
    },
    mounted() {
      this.loadSvg();
      this.fetchCoordinates();
  
      this.socket = io('http://localhost:3000');
      this.socket.on('new-coordinate', (coordinate) => {
        this.point = coordinate; // Update single coordinate
      });
    },
    beforeUnmount() {
      if (this.socket) {
        this.socket.disconnect();
      }
    },
  };
  </script>
  
  <style scoped>
  .rectangle-map {
    position: relative;
    width: 100%;
    height: 500px;
    border: 1px solid #000;
  }
  .floorplan {
    width: 100%;
    height: 100%;
  }
  .markers {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
  }
  .coordinates {
    position: absolute;
    top: 10px;
    left: 10px;
    background: rgba(255, 255, 255, 0.8);
    padding: 5px;
    border: 1px solid #ccc;
    border-radius: 3px;
    font-size: 14px;
  }
  .info {
    margin-top: 20px;
    font-size: 18px;
    font-weight: bold;
  }
  .wall {
    fill: gray;
    pointer-events: none; /* Walls are not clickable */
  }
  .room {
    fill: lightblue;
    cursor: pointer;
  }
  .room:hover {
    fill: darkblue;
  }
  </style>
  