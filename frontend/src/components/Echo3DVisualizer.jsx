import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';

export default function Echo3DVisualizer({ results, selectedPair, onSelectPair, explain = true }) {
  const containerRef = useRef(null);
  const [viewMode, setViewMode] = useState('radar'); // 'radar' | 'constellation'
  const [hoveredNode, setHoveredNode] = useState(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Scene, Camera, Renderer
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x0b0f19, 0.002);

    const width = container.clientWidth || 600;
    const height = container.clientHeight || 360;

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(0, 30, 85);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.2;
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    // Group holding entire 3D structure
    const rootGroup = new THREE.Group();
    scene.add(rootGroup);

    // 1. Central Holographic Core (Wireframe Icosahedron)
    const coreGeo = new THREE.IcosahedronGeometry(12, 2);
    const coreMat = new THREE.MeshBasicMaterial({
      color: 0x6366f1,
      wireframe: true,
      transparent: true,
      opacity: 0.35,
    });
    const coreMesh = new THREE.Mesh(coreGeo, coreMat);
    rootGroup.add(coreMesh);

    // 2. Inner Pulsing Core
    const innerGeo = new THREE.SphereGeometry(6, 16, 16);
    const innerMat = new THREE.MeshBasicMaterial({
      color: 0xa855f7,
      wireframe: true,
      transparent: true,
      opacity: 0.25,
    });
    const innerMesh = new THREE.Mesh(innerGeo, innerMat);
    rootGroup.add(innerMesh);

    // 3. Floating 3D Concentric Radar Rings
    const ringMat1 = new THREE.MeshBasicMaterial({
      color: 0x06b6d4,
      wireframe: true,
      transparent: true,
      opacity: 0.45,
    });
    const ringMat2 = new THREE.MeshBasicMaterial({
      color: 0x6366f1,
      wireframe: true,
      transparent: true,
      opacity: 0.4,
    });
    const ringMat3 = new THREE.MeshBasicMaterial({
      color: 0xf43f5e,
      wireframe: true,
      transparent: true,
      opacity: 0.3,
    });

    const ring1 = new THREE.Mesh(new THREE.TorusGeometry(22, 0.2, 16, 100), ringMat1);
    const ring2 = new THREE.Mesh(new THREE.TorusGeometry(32, 0.25, 16, 100), ringMat2);
    const ring3 = new THREE.Mesh(new THREE.TorusGeometry(42, 0.3, 16, 100), ringMat3);

    ring1.rotation.x = Math.PI / 3;
    ring2.rotation.y = Math.PI / 4;
    ring3.rotation.z = Math.PI / 6;

    rootGroup.add(ring1);
    rootGroup.add(ring2);
    rootGroup.add(ring3);

    // 4. Background Particle Field
    const particleCount = 200;
    const particleGeo = new THREE.BufferGeometry();
    const particlePositions = new Float32Array(particleCount * 3);
    for (let i = 0; i < particleCount * 3; i += 3) {
      particlePositions[i] = (Math.random() - 0.5) * 140;
      particlePositions[i + 1] = (Math.random() - 0.5) * 140;
      particlePositions[i + 2] = (Math.random() - 0.5) * 140;
    }
    particleGeo.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));
    const particleMat = new THREE.PointsMaterial({
      size: 1.2,
      color: 0x94a3b8,
      transparent: true,
      opacity: 0.4,
    });
    const particlePoints = new THREE.Points(particleGeo, particleMat);
    rootGroup.add(particlePoints);

    // 5. Dynamic Student Nodes & Connections
    const studentMeshes = [];
    const linkLines = [];
    const submissions = results?.submissions || [];
    const flaggedPairs = results?.flagged_pairs || [];

    // Position student nodes on sphere
    const radius = 32;
    const studentPositions = {};

    submissions.forEach((sub, idx) => {
      // Golden spiral distribution on sphere
      const phi = Math.acos(-1 + (2 * idx) / Math.max(submissions.length, 1));
      const theta = Math.sqrt(submissions.length * Math.PI) * phi;

      const x = radius * Math.cos(theta) * Math.sin(phi);
      const y = radius * Math.sin(theta) * Math.sin(phi);
      const z = radius * Math.cos(phi);

      studentPositions[sub.name] = new THREE.Vector3(x, y, z);

      // Node geometry
      const isFlagged = flaggedPairs.some(
        (p) => p.student_a === sub.name || p.student_b === sub.name
      );

      const nodeGeo = new THREE.SphereGeometry(isFlagged ? 2.0 : 1.2, 16, 16);
      const nodeMat = new THREE.MeshBasicMaterial({
        color: isFlagged ? 0xf43f5e : 0x06b6d4,
      });
      const nodeMesh = new THREE.Mesh(nodeGeo, nodeMat);
      nodeMesh.position.set(x, y, z);
      nodeMesh.userData = { studentName: sub.name, isFlagged };

      // Halo ring around flagged students
      if (isFlagged) {
        const haloGeo = new THREE.RingGeometry(2.5, 3.2, 24);
        const haloMat = new THREE.MeshBasicMaterial({
          color: 0xf43f5e,
          side: THREE.DoubleSide,
          transparent: true,
          opacity: 0.6,
        });
        const halo = new THREE.Mesh(haloGeo, haloMat);
        halo.lookAt(0, 0, 0);
        nodeMesh.add(halo);
      }

      rootGroup.add(nodeMesh);
      studentMeshes.push(nodeMesh);
    });

    // 6. Connect Flagged Pairs with Glowing Laser Beams
    flaggedPairs.forEach((pair) => {
      const posA = studentPositions[pair.student_a];
      const posB = studentPositions[pair.student_b];

      if (posA && posB) {
        // Curved line through 3D space
        const midPoint = posA.clone().add(posB).multiplyScalar(0.5);
        // Push mid-point outward away from center
        midPoint.normalize().multiplyScalar(radius * 1.25);

        const curve = new THREE.QuadraticBezierCurve3(posA, midPoint, posB);
        const points = curve.getPoints(30);
        const lineGeo = new THREE.BufferGeometry().setFromPoints(points);

        let lineColor = 0x06b6d4;
        let lineOpacity = 0.75;
        let lineWidth = 2;

        if (explain && pair.label) {
          if (pair.label === 'likely copy') {
            lineColor = 0xff1744; // Neon Red
            lineOpacity = 0.95;
            lineWidth = 3;
          } else if (pair.label === 'paraphrase') {
            lineColor = 0xffab00; // Neon Amber
            lineOpacity = 0.9;
            lineWidth = 2.5;
          } else if (pair.label === 'shared source') {
            lineColor = 0x00e5ff; // Electric Cyan
            lineOpacity = 0.8;
            lineWidth = 2;
          } else if (pair.label === 'coincidence') {
            lineColor = 0x64748b; // Steel Muted
            lineOpacity = 0.35;
            lineWidth = 1;
          }
        } else {
          // Standard Semantic Mode (Gemma Off): color by score
          lineColor = pair.score >= 0.95 ? 0xf43f5e : (pair.score >= 0.88 ? 0x06b6d4 : 0x8b5cf6);
          lineOpacity = 0.8;
          lineWidth = pair.score >= 0.95 ? 3 : 2;
        }

        const lineMat = new THREE.LineBasicMaterial({
          color: lineColor,
          transparent: true,
          opacity: lineOpacity,
          linewidth: lineWidth,
        });

        const lineMesh = new THREE.Line(lineGeo, lineMat);
        lineMesh.userData = { pair };
        rootGroup.add(lineMesh);
        linkLines.push(lineMesh);
      }
    });

    // Raycaster for mouse interaction
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    let isDragging = false;
    let prevMousePos = { x: 0, y: 0 };
    let targetRotation = { x: 0.2, y: 0.3 };

    const onMouseDown = (e) => {
      isDragging = true;
      prevMousePos = { x: e.clientX, y: e.clientY };
    };

    const onMouseMove = (e) => {
      const rect = container.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      if (isDragging) {
        const deltaX = e.clientX - prevMousePos.x;
        const deltaY = e.clientY - prevMousePos.y;
        targetRotation.y += deltaX * 0.008;
        targetRotation.x += deltaY * 0.008;
        prevMousePos = { x: e.clientX, y: e.clientY };
      } else {
        // Parallax hover check
        raycaster.setFromCamera(mouse, camera);
        const intersects = raycaster.intersectObjects(studentMeshes);
        if (intersects.length > 0) {
          const hit = intersects[0].object;
          setHoveredNode(hit.userData.studentName);
          document.body.style.cursor = 'pointer';
        } else {
          setHoveredNode(null);
          document.body.style.cursor = 'default';
        }
      }
    };

    const onMouseUp = () => {
      isDragging = false;
    };

    container.addEventListener('mousedown', onMouseDown);
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);

    // Resize handler
    const handleResize = () => {
      if (!container) return;
      const newWidth = container.clientWidth;
      const newHeight = container.clientHeight;
      camera.aspect = newWidth / newHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(newWidth, newHeight);
    };
    window.addEventListener('resize', handleResize);

    // Animation Loop
    let animationFrameId;
    let clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const elapsed = clock.getElapsedTime();

      // Smooth damped rotation
      rootGroup.rotation.y += (targetRotation.y - rootGroup.rotation.y) * 0.08;
      rootGroup.rotation.x += (targetRotation.x - rootGroup.rotation.x) * 0.08;

      // Auto rotation when not dragging
      if (!isDragging) {
        targetRotation.y += 0.003;
      }

      // Pulse core
      coreMesh.rotation.y = elapsed * 0.2;
      coreMesh.rotation.x = elapsed * 0.15;
      const scale = 1 + Math.sin(elapsed * 2) * 0.05;
      coreMesh.scale.set(scale, scale, scale);

      // Rotate radar rings
      ring1.rotation.z += 0.008;
      ring2.rotation.x += 0.006;
      ring3.rotation.y += 0.004;

      renderer.render(scene, camera);
    };

    animate();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', handleResize);
      container.removeEventListener('mousedown', onMouseDown);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      document.body.style.cursor = 'default';
      renderer.dispose();
    };
  }, [results]);

  return (
    <div className="three-visualizer-card">
      <div className="visualizer-header">
        <div className="visualizer-title-wrap">
          <div className="visualizer-indicator">
            <span className="visualizer-pulse"></span>
            3D SPATIAL ECHO MODEL
          </div>
          <h3 className="visualizer-heading">Holographic Submission Radar</h3>
        </div>

        <div className="visualizer-meta">
          {explain ? (
            <span className="vis-tag purple">
              ✨ Gemma 3 Active
            </span>
          ) : (
            <span className="vis-tag muted">
              ○ Gemma Disabled
            </span>
          )}
          {results?.submissions ? (
            <>
              <span className="vis-tag green">
                ● {results.submissions.length} Nodes Mapped
              </span>
              <span className="vis-tag ruby">
                ⚡ {results.flagged_pairs?.length || 0} Similarity Beams
              </span>
            </>
          ) : (
            <span className="vis-tag cyan">● Standby Scan Mesh Active</span>
          )}
        </div>
      </div>

      <div className="three-canvas-container" ref={containerRef}>
        {hoveredNode && (
          <div className="three-hover-tooltip">
            <strong>Student:</strong> {hoveredNode}
          </div>
        )}
      </div>

      <div className="visualizer-footer">
        <span className="vis-tip">
          🖱️ Click & drag to rotate 3D model • Hover over node spheres for identity
        </span>
        <div className="vis-legend">
          {explain ? (
            <>
              <span className="vis-legend-item">
                <span className="dot" style={{ backgroundColor: '#ff1744' }}></span> Likely Copy Beam
              </span>
              <span className="vis-legend-item">
                <span className="dot" style={{ backgroundColor: '#ffab00' }}></span> Paraphrase Beam
              </span>
              <span className="vis-legend-item">
                <span className="dot" style={{ backgroundColor: '#00e5ff' }}></span> Shared Source Beam
              </span>
            </>
          ) : (
            <>
              <span className="vis-legend-item">
                <span className="dot ruby"></span> Score &ge; 95%
              </span>
              <span className="vis-legend-item">
                <span className="dot cyan"></span> Score &lt; 95%
              </span>
            </>
          )}
          <span className="vis-legend-item">
            <span className="dot purple"></span> Holographic Core
          </span>
        </div>
      </div>
    </div>
  );
}
