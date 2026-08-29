"use client";

import React, { useEffect, useRef } from "react";

export interface BorromeanBannerProps {
  height?: number | string;
  width?: number | string;
  className?: string;
  style?: React.CSSProperties;
  speed?: number;
}

/**
 * BorromeanBanner - 16:9 Banner Component for Portfolios
 * Exact WebGL render of the 3D Borromean Rings with perforated gold mesh, metallic rims, and seamless diagonal rotation.
 */
export default function BorromeanBanner({
  height = "100%",
  width = "100%",
  className,
  style,
  speed = 1.0,
}: BorromeanBannerProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let active = true;
    let animId: number;

    const init = async () => {
      let THREE = (window as any).THREE;
      if (!THREE) {
        await new Promise<void>((resolve, reject) => {
          const script = document.createElement("script");
          script.src = "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js";
          script.async = true;
          script.onload = () => resolve();
          script.onerror = () => reject(new Error("Three.js failed to load"));
          document.head.appendChild(script);
        });
        THREE = (window as any).THREE;
      }

      if (!THREE || !active) return;
      const container = containerRef.current;
      if (!container) return;

      const scene = new THREE.Scene();
      scene.background = new THREE.Color(0x000000);

      const w = container.clientWidth || 1600;
      const h = container.clientHeight || 900;

      const camera = new THREE.PerspectiveCamera(40, w / h, 0.1, 100);
      camera.position.set(0, 0, 7.6);

      const renderer = new THREE.WebGLRenderer({
        alpha: false,
        antialias: true,
        powerPreference: "high-performance",
        precision: "highp",
      });

      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2.5));
      renderer.setSize(w, h);
      renderer.outputEncoding = THREE.sRGBEncoding || 3001;

      while (container.firstChild) {
        container.removeChild(container.firstChild);
      }
      container.appendChild(renderer.domElement);

      const dom = renderer.domElement;
      dom.style.display = "block";
      dom.style.width = "100%";
      dom.style.height = "100%";

      // Lighting
      scene.add(new THREE.AmbientLight(0xffffff, 1.4));
      const keyLight = new THREE.DirectionalLight(0xfff8ee, 3.4);
      keyLight.position.set(6, 8, 7);
      scene.add(keyLight);

      const fillLight = new THREE.DirectionalLight(0x0088cc, 2.4);
      fillLight.position.set(-6, -4, -5);
      scene.add(fillLight);

      const rimLight = new THREE.PointLight(0xfc6a03, 3.4, 30);
      rimLight.position.set(0, 5, -6);
      scene.add(rimLight);

      const bounceLight = new THREE.PointLight(0xa07838, 2.2, 20);
      bounceLight.position.set(0, -6, 3);
      scene.add(bounceLight);

      // Perforation texture
      const texCanvas = document.createElement("canvas");
      texCanvas.width = 2048;
      texCanvas.height = 2048;
      const ctx = texCanvas.getContext("2d")!;
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = "high";

      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, 2048, 2048);

      const holeR = 58.0;
      const stepX = 184.0;
      const stepY = 159.34;

      for (let y = -80; y < 2128; y += stepY) {
        const row = Math.round(y / stepY);
        const offsetX = row % 2 === 0 ? 0 : stepX / 2;
        for (let x = -80; x < 2128; x += stepX) {
          const grad = ctx.createRadialGradient(x + offsetX, y, holeR * 0.88, x + offsetX, y, holeR);
          grad.addColorStop(0, "rgba(0,0,0,1)");
          grad.addColorStop(0.85, "rgba(0,0,0,1)");
          grad.addColorStop(1, "rgba(255,255,255,1)");

          ctx.fillStyle = grad;
          ctx.beginPath();
          ctx.arc(x + offsetX, y, holeR, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      const perforatedTex = new THREE.CanvasTexture(texCanvas);
      perforatedTex.wrapS = THREE.RepeatWrapping;
      perforatedTex.wrapT = THREE.RepeatWrapping;
      perforatedTex.repeat.set(3.8, 2.8);
      perforatedTex.generateMipmaps = true;
      perforatedTex.minFilter = THREE.LinearMipmapLinearFilter;
      perforatedTex.magFilter = THREE.LinearFilter;

      const rimMaterial = new THREE.MeshStandardMaterial({
        color: 0xd4b06a,
        metalness: 0.92,
        roughness: 0.2,
      });

      const meshMaterial = new THREE.MeshStandardMaterial({
        color: 0xc49f56,
        metalness: 0.9,
        roughness: 0.26,
        alphaMap: perforatedTex,
        transparent: true,
        opacity: 0.98,
        depthWrite: false,
        side: THREE.DoubleSide,
      });

      const group = new THREE.Group();
      scene.add(group);

      const a = 2.25;
      const b = 1.35;
      const h = 0.38;
      const planes: Array<"xy" | "yz" | "zx"> = ["xy", "yz", "zx"];

      planes.forEach((plane) => {
        const curve = new (THREE.Curve as any)();
        curve.getPoint = function (t: number) {
          const theta = t * Math.PI * 2;
          const cos = Math.cos(theta);
          const sin = Math.sin(theta);
          const saddle = h * Math.sin(2 * theta);

          if (plane === "xy") return new THREE.Vector3(a * cos, b * sin, saddle);
          if (plane === "yz") return new THREE.Vector3(saddle, a * cos, b * sin);
          return new THREE.Vector3(b * sin, saddle, a * cos);
        };

        const tubeGeom = new THREE.TubeGeometry(curve, 512, 0.045, 32, true);
        const tubeMesh = new THREE.Mesh(tubeGeom, rimMaterial);
        group.add(tubeMesh);

        const surfGeom = new THREE.BufferGeometry();
        const uSegs = 240;
        const vSegs = 64;
        const positions: number[] = [];
        const uvs: number[] = [];
        const indices: number[] = [];

        for (let j = 0; j <= vSegs; j++) {
          const v = j / vSegs;
          const curA = (a - 0.02) * v;
          const curB = (b - 0.02) * v;
          const curH = h * Math.pow(v, 1.4);

          for (let i = 0; i <= uSegs; i++) {
            const u = i / uSegs;
            const theta = u * Math.PI * 2;
            const cos = Math.cos(theta);
            const sin = Math.sin(theta);
            const saddle = curH * Math.sin(2 * theta);

            let x = 0, y = 0, z = 0;
            if (plane === "xy") {
              x = curA * cos;
              y = curB * sin;
              z = saddle;
            } else if (plane === "yz") {
              x = saddle;
              y = curA * cos;
              z = curB * sin;
            } else {
              x = curB * sin;
              y = saddle;
              z = curA * cos;
            }

            positions.push(x, y, z);
            uvs.push(u * 5, v * 3);
          }
        }

        for (let j = 0; j < vSegs; j++) {
          for (let i = 0; i < uSegs; i++) {
            const p1 = j * (uSegs + 1) + i;
            const p2 = (j + 1) * (uSegs + 1) + i;
            const p3 = (j + 1) * (uSegs + 1) + (i + 1);
            const p4 = j * (uSegs + 1) + (i + 1);
            indices.push(p1, p2, p4);
            indices.push(p2, p3, p4);
          }
        }

        surfGeom.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
        surfGeom.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
        surfGeom.setIndex(indices);
        surfGeom.computeVertexNormals();

        const surfMesh = new THREE.Mesh(surfGeom, meshMaterial);
        group.add(surfMesh);
      });

      // Diagonal rotation axis & initial tilt
      const diagonalAxis = new THREE.Vector3(0.68, 1.0, 0.46).normalize();
      const initialTilt = new THREE.Euler(0.48, 0.52, 0.22);
      let currentAngle = 0;

      const handleResize = () => {
        if (!container) return;
        const curW = container.clientWidth;
        const curH = container.clientHeight;
        camera.aspect = curW / curH;
        camera.updateProjectionMatrix();
        renderer.setSize(curW, curH);
      };
      window.addEventListener("resize", handleResize);

      let time = 0;
      const animate = () => {
        animId = requestAnimationFrame(animate);
        time += 0.012 * speed;
        group.rotation.y += (0.0055 + 0.0035 * Math.sin(time * 0.73) + 0.0022 * Math.cos(time * 1.37)) * speed;
        group.rotation.x += (0.0032 * Math.cos(time * 0.51) + 0.0028 * Math.sin(time * 0.93 + 1.2)) * speed;
        group.rotation.z += (0.0026 * Math.sin(time * 0.41) + 0.0020 * Math.cos(time * 0.81 + 2.3)) * speed;
        renderer.render(scene, camera);
      };
      animate();

      return () => {
        window.removeEventListener("resize", handleResize);
        cancelAnimationFrame(animId);
        renderer.dispose();
      };
    };

    init();

    return () => {
      active = false;
    };
  }, [speed]);

  return (
    <div
      ref={containerRef}
      className={className}
      style={{
        width,
        height,
        aspectRatio: "16 / 9",
        backgroundColor: "#000000",
        position: "relative",
        overflow: "hidden",
        ...style,
      }}
    />
  );
}
