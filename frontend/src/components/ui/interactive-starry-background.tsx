"use client";

import React, { useRef, useEffect, useState } from 'react';

interface Star {
  x: number; // Position on the larger virtual canvas
  y: number; // Position on the larger virtual canvas
  size: number;
  opacity: number;
}

interface Meteor {
  x: number;
  y: number;
  vx: number; // Velocity x
  vy: number; // Velocity y
  length: number;
  opacity: number;
  maxOpacity: number;
  life: number; // Current lifespan
  maxLife: number; // Max lifespan for fading
  traveledDistance: number; // To track for explosion
  exploded: boolean;
  explosionParticles: ExplosionParticle[];
  explosionImage: HTMLImageElement | null;
  explosionImageSize: { width: number, height: number } | null;
}

interface ExplosionParticle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  opacity: number;
  life: number;
  maxLife: number;
}

interface InteractiveStarryBackgroundProps {
  starCount?: number;
  starColor?: string;
  starSizeMultiplier?: number;
  starOpacityBase?: number;
  panSensitivity?: number; // How much the background pans with mouse movement
  panEasing?: number; // How quickly the pan smooths out
  virtualSizeMultiplier?: number; // How much larger the virtual canvas is than the viewport
  meteorSpawnInterval?: number; // Average ms between meteor spawns
  meteorColor?: string;
  meteorExplosionDistance?: number;
  explosionParticleCount?: number;
  explosionParticleSpeed?: number;
  explosionParticleDuration?: number;
  cryptoLogoPaths?: string[];
}

const InteractiveStarryBackground: React.FC<InteractiveStarryBackgroundProps> = ({
  starCount = 700, // Moderate star count for constellation-like clusters
  starColor = 'rgba(255, 255, 255, 0.7)', // More visible stars
  starSizeMultiplier = 1.5, // Stars 0.3px to 1.8px
  starOpacityBase = 0.5, // Opacity 0.5 to 1.0
  panSensitivity = 0.2, // Lower values mean less panning for mouse movement
  panEasing = 0.08, // Controls smoothness of panning
  virtualSizeMultiplier = 1.5, // Virtual canvas is 1.5x viewport size
  meteorSpawnInterval = 1500, // Increased spawn rate (was 2500)
  meteorColor = 'rgba(220, 220, 255, 0.7)', // Slightly blueish white for meteors
  meteorExplosionDistance = 150, // Distance before meteor explodes
  explosionParticleCount = 50, // Number of particles per explosion
  explosionParticleSpeed = 1.5, // Speed of explosion particles
  explosionParticleDuration = 70, // Frames for particles to last
  cryptoLogoPaths = ['/logos/btc.png', '/logos/eth.png', '/logos/sol.png'], // Placeholder paths
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const starsRef = useRef<Star[]>([]);
  const meteorsRef = useRef<Meteor[]>([]);
  const loadedCryptoImagesRef = useRef<HTMLImageElement[]>([]);
  const mousePositionRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const currentPanRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const targetPanRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const animationFrameIdRef = useRef<number | null>(null);
  const lastMeteorSpawnTimeRef = useRef<number>(Date.now());

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let virtualWidth: number;
    let virtualHeight: number;
    let panLimitX: number;
    let panLimitY: number;

    const initializeStarsAndCanvas = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
      mousePositionRef.current = { x: canvas.width / 2, y: canvas.height / 2 }; // Initialize mouse at center

      virtualWidth = canvas.width * virtualSizeMultiplier;
      virtualHeight = canvas.height * virtualSizeMultiplier;

      // Calculate panning limits: how far can we pan from the center (0,0) of the virtual canvas
      // The view is centered on (0,0) of the pan coordinates. Max pan moves this center to the edge of pannable area.
      panLimitX = (virtualWidth - canvas.width) / 2;
      panLimitY = (virtualHeight - canvas.height) / 2;

      starsRef.current = [];
      for (let i = 0; i < starCount; i++) {
        starsRef.current.push({
          // Spread stars across the virtual canvas, centered around (0,0)
          x: (Math.random() - 0.5) * virtualWidth,
          y: (Math.random() - 0.5) * virtualHeight,
          size: Math.random() * starSizeMultiplier + 0.3,
          opacity: Math.random() * (1 - starOpacityBase) + starOpacityBase,
        });
      }
      meteorsRef.current = []; // Clear meteors on resize
    };

    const preloadImages = () => {
      loadedCryptoImagesRef.current = [];
      cryptoLogoPaths.forEach(path => {
        const img = new Image();
        img.src = path;
        // img.onload = () => { /* Optional: handle loaded event */ };
        // img.onerror = () => { console.error(`Failed to load image: ${path}`); };
        loadedCryptoImagesRef.current.push(img);
      });
    };

    const spawnMeteor = () => {
      const edge = Math.floor(Math.random() * 4); // 0: top, 1: right, 2: bottom, 3: left
      let x, y, vx, vy;
      const speed = Math.random() * 2 + 1; // Slower speed (was Math.random() * 3 + 2)
      const angleDeviation = (Math.random() - 0.5) * (Math.PI / 4); // Deviate up to 45 degrees from direct across

      switch (edge) {
        case 0: // Top edge
          x = Math.random() * canvas.width;
          y = -20; // Start off-screen
          vx = Math.sin(Math.PI / 2 + angleDeviation) * speed;
          vy = Math.cos(Math.PI / 2 + angleDeviation) * speed;
          break;
        case 1: // Right edge
          x = canvas.width + 20;
          y = Math.random() * canvas.height;
          vx = -Math.cos(angleDeviation) * speed;
          vy = Math.sin(angleDeviation) * speed;
          break;
        case 2: // Bottom edge
          x = Math.random() * canvas.width;
          y = canvas.height + 20;
          vx = Math.sin(-Math.PI / 2 + angleDeviation) * speed;
          vy = -Math.cos(-Math.PI / 2 + angleDeviation) * speed;
          break;
        default: // Left edge (case 3)
          x = -20;
          y = Math.random() * canvas.height;
          vx = Math.cos(angleDeviation) * speed;
          vy = Math.sin(angleDeviation) * speed;
          break;
      }

      meteorsRef.current.push({
        x, y, vx, vy,
        length: Math.random() * 100 + 50, // Length of meteor tail
        opacity: 0,
        maxOpacity: Math.random() * 0.5 + 0.3, // Max opacity between 0.3 and 0.8
        life: 0,
        maxLife: 100 + Math.random() * 100, // Fade in/out over 100-200 frames
        traveledDistance: 0,
        exploded: false,
        explosionParticles: [],
        explosionImage: null,
        explosionImageSize: null,
      });
    };

    const handleMouseMove = (event: MouseEvent) => {
      mousePositionRef.current = { x: event.clientX, y: event.clientY };
    };

    const animate = () => {
      const now = Date.now();
      if (now - lastMeteorSpawnTimeRef.current > meteorSpawnInterval * (0.5 + Math.random())) { // Add some randomness
        spawnMeteor();
        lastMeteorSpawnTimeRef.current = now;
      }

      // Calculate target pan based on mouse position relative to screen center
      const dx = mousePositionRef.current.x - canvas.width / 2;
      const dy = mousePositionRef.current.y - canvas.height / 2;

      // Target pan is inverted: mouse right -> view right (starfield moves left)
      targetPanRef.current.x = Math.max(-panLimitX, Math.min(panLimitX, -dx * panSensitivity));
      targetPanRef.current.y = Math.max(-panLimitY, Math.min(panLimitY, -dy * panSensitivity));
      
      // Ease current pan towards target pan
      currentPanRef.current.x += (targetPanRef.current.x - currentPanRef.current.x) * panEasing;
      currentPanRef.current.y += (targetPanRef.current.y - currentPanRef.current.y) * panEasing;

      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.save();
      // Translate to the center of the screen, then apply pan, then draw stars relative to virtual center (0,0)
      ctx.translate(canvas.width / 2 + currentPanRef.current.x, canvas.height / 2 + currentPanRef.current.y);

      starsRef.current.forEach(star => {
        ctx.beginPath();
        ctx.arc(star.x, star.y, star.size, 0, Math.PI * 2);
        ctx.fillStyle = starColor.replace(/,\s*([\d.]+)\)/, `, ${star.opacity})`); // Adjust opacity of starColor
        ctx.fill();
      });

      // Draw meteors (not affected by pan, drawn directly on viewport)
      ctx.save();
      meteorsRef.current = meteorsRef.current.filter(meteor => {
        if (!meteor.exploded) {
          meteor.x += meteor.vx;
          meteor.y += meteor.vy;
          meteor.traveledDistance += Math.sqrt(meteor.vx**2 + meteor.vy**2);
          meteor.life++;

          // Fade in and out logic for meteor itself
          if (meteor.life < meteor.maxLife / 2) {
            meteor.opacity = (meteor.life / (meteor.maxLife / 2)) * meteor.maxOpacity;
          } else {
            meteor.opacity = (1 - (meteor.life - meteor.maxLife / 2) / (meteor.maxLife / 2)) * meteor.maxOpacity;
          }

          if (meteor.opacity <= 0 || meteor.life >= meteor.maxLife) {
             // If meteor fades out before exploding, mark for removal without explosion
            if (meteor.explosionParticles.length === 0) return false;
          }


          // Check for explosion
          if (meteor.traveledDistance > meteorExplosionDistance && !meteor.exploded) {
            meteor.exploded = true;
            if (loadedCryptoImagesRef.current.length > 0) {
              meteor.explosionImage = loadedCryptoImagesRef.current[Math.floor(Math.random() * loadedCryptoImagesRef.current.length)];
              const baseSize = Math.random() * 30 + 20; // Random base size between 20 and 50
              const aspectRatio = meteor.explosionImage.naturalWidth / meteor.explosionImage.naturalHeight;
              meteor.explosionImageSize = {
                width: baseSize * (aspectRatio > 1 ? 1 : aspectRatio),
                height: baseSize * (aspectRatio < 1 ? 1 : 1 / aspectRatio),
              };
            }

            for (let i = 0; i < explosionParticleCount; i++) {
              const angle = Math.random() * Math.PI * 2;
              const speed = Math.random() * explosionParticleSpeed + 0.5;
              meteor.explosionParticles.push({
                x: meteor.x,
                y: meteor.y,
                vx: Math.cos(angle) * speed,
                vy: Math.sin(angle) * speed,
                size: Math.random() * 2 + 1,
                opacity: 1,
                life: 0,
                maxLife: explosionParticleDuration,
              });
            }
            meteor.opacity = 0; // Hide meteor tail immediately on explosion
          }
        }

        // Handle explosion particles
        if (meteor.exploded) {
          meteor.explosionParticles.forEach(p => {
            p.x += p.vx;
            p.y += p.vy;
            p.life++;
            p.opacity = 1 - (p.life / p.maxLife);
          });

          meteor.explosionParticles = meteor.explosionParticles.filter(p => p.opacity > 0 && p.life < p.maxLife);

          // Draw particles
          meteor.explosionParticles.forEach(p => {
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
            const particleColorMatch = meteorColor.match(/(rgba?\([^,]+,[^,]+,[^,]+)/);
            const particleBaseColor = particleColorMatch ? particleColorMatch[1] : 'rgba(255,255,255)';
            ctx.fillStyle = `${particleBaseColor},${p.opacity})`;
            ctx.fill();
          });
          
          // Draw crypto symbol (now image)
          if (meteor.explosionImage && meteor.explosionImageSize && meteor.explosionParticles.length > 0) {
            const firstParticle = meteor.explosionParticles[0];
            if (firstParticle && meteor.explosionImage.complete && meteor.explosionImage.naturalHeight !== 0) { // Check image loaded
                const imageOpacity = firstParticle.opacity * 0.9; // Slightly more visible than text
                ctx.save();
                ctx.globalAlpha = imageOpacity;
                const imgWidth = meteor.explosionImageSize.width;
                const imgHeight = meteor.explosionImageSize.height;
                ctx.drawImage(meteor.explosionImage, meteor.x - imgWidth / 2, meteor.y - imgHeight / 2, imgWidth, imgHeight);
                ctx.restore();
            }
          }
          
          // If exploded and all particles are gone, remove the meteor
          if (meteor.explosionParticles.length === 0) return false;
        }

        // Draw meteor tail if not exploded
        if (!meteor.exploded && meteor.opacity > 0) {
          ctx.beginPath();
          ctx.moveTo(meteor.x, meteor.y);
          ctx.lineTo(meteor.x - meteor.vx * meteor.length, meteor.y - meteor.vy * meteor.length);
          
          const gradient = ctx.createLinearGradient(meteor.x, meteor.y, meteor.x - meteor.vx * meteor.length, meteor.y - meteor.vy * meteor.length);
          const trailColorMatch = meteorColor.match(/(rgba?\([^,]+,[^,]+,[^,]+)/);
          const baseColorString = trailColorMatch ? trailColorMatch[1] : 'rgba(255,255,255)';
          gradient.addColorStop(0, `${baseColorString},${meteor.opacity})`);
          gradient.addColorStop(1, `${baseColorString},0)`);
          ctx.strokeStyle = gradient;
          ctx.lineWidth = 2;
          ctx.stroke();
        }
        
        // Keep meteor if it's not exploded yet or if it has active particles
        return true;
      });
      ctx.restore(); // Restore from meteor specific drawing context

      ctx.restore(); // Restore from pan and star drawing context
      animationFrameIdRef.current = requestAnimationFrame(animate);
    };

    initializeStarsAndCanvas();
    preloadImages(); // Preload images
    window.addEventListener('resize', () => {
        initializeStarsAndCanvas();
        preloadImages(); // Re-evaluate on resize if paths could change, though unlikely here
    });
    window.addEventListener('mousemove', handleMouseMove);
    
    animate();

    return () => {
      window.removeEventListener('resize', initializeStarsAndCanvas);
      window.removeEventListener('mousemove', handleMouseMove);
      if (animationFrameIdRef.current) {
        cancelAnimationFrame(animationFrameIdRef.current);
      }
    };
  }, [starCount, starColor, starSizeMultiplier, starOpacityBase, panSensitivity, panEasing, virtualSizeMultiplier, meteorSpawnInterval, meteorColor, meteorExplosionDistance, explosionParticleCount, explosionParticleSpeed, explosionParticleDuration, cryptoLogoPaths]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        zIndex: -1,
        background: 'radial-gradient(ellipse at bottom, #0d1a26 0%, #040608 100%)', // Keep a dark base
      }}
    />
  );
};

export { InteractiveStarryBackground }; 