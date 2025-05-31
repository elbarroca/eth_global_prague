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

// New interface for Planets
interface Planet {
  x: number;
  y: number;
  size: number;
  baseColor: string;
  detailColor?: string;
  ring?: {
    color: string;
    angle: number; // Angle of the rings in radians
    width: number; // Width of the ring band
    radiusFactor: number; // How far out the ring is from the planet surface (e.g., 1.5x planet radius)
  };
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
  planetCount?: number; // New prop for number of planets
  scrollPanSensitivity?: number; // New prop for scroll-based panning
}

// Constants for planet generation
const DEFAULT_PLANET_COUNT = 5;
const PLANET_MIN_SIZE = 2;
const PLANET_MAX_SIZE = 6;
const PLANET_COLORS = [
  { base: '#4A7A8C', detail: '#70A5B9' }, // Bluish
  { base: '#D9A467', detail: '#F0C89B' }, // Sandy/Yellowish
  { base: '#A94E4E', detail: '#D47F7F' }, // Reddish
  { base: '#5E8C6A', detail: '#8EBE9A' }, // Greenish
  { base: '#8C5A8C', detail: '#B98DC3' }, // Purplish
  { base: '#B0B0B0', detail: '#E0E0E0' }, // Greyish
];
const PLANET_RING_COLORS = ['rgba(200, 200, 180, 0.7)', 'rgba(180, 190, 200, 0.7)'];

const InteractiveStarryBackground: React.FC<InteractiveStarryBackgroundProps> = ({
  starCount = 700,
  starColor = 'rgba(255, 255, 255, 0.7)',
  starSizeMultiplier = 1.5,
  starOpacityBase = 0.5,
  panSensitivity = 0.2,
  panEasing = 0.08,
  virtualSizeMultiplier = 1.5,
  meteorSpawnInterval = 1500,
  meteorColor = 'rgba(220, 220, 255, 0.7)',
  meteorExplosionDistance = 250,
  explosionParticleCount = 50,
  explosionParticleSpeed = 1.5,
  explosionParticleDuration = 70,
  cryptoLogoPaths = ['/logos/btc.png', '/logos/eth.png', '/logos/sol.png'],
  planetCount = DEFAULT_PLANET_COUNT, // Use new constant
  scrollPanSensitivity = 0.1, // Default value for scroll sensitivity
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const starsRef = useRef<Star[]>([]);
  const planetsRef = useRef<Planet[]>([]); // Ref for planets
  const meteorsRef = useRef<Meteor[]>([]);
  const loadedCryptoImagesRef = useRef<HTMLImageElement[]>([]);
  const mousePositionRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const scrollOffsetYRef = useRef<number>(0); // Ref to store scroll Y offset
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
      mousePositionRef.current = { x: canvas.width / 2, y: canvas.height / 2 };

      virtualWidth = canvas.width * virtualSizeMultiplier;
      virtualHeight = canvas.height * virtualSizeMultiplier;

      panLimitX = (virtualWidth - canvas.width) / 2;
      panLimitY = (virtualHeight - canvas.height) / 2;

      starsRef.current = [];
      for (let i = 0; i < starCount; i++) {
        starsRef.current.push({
          x: (Math.random() - 0.5) * virtualWidth,
          y: (Math.random() - 0.5) * virtualHeight,
          size: Math.random() * starSizeMultiplier + 0.3,
          opacity: Math.random() * (1 - starOpacityBase) + starOpacityBase,
        });
      }

      planetsRef.current = [];
      for (let i = 0; i < planetCount; i++) {
        const colorSet = PLANET_COLORS[i % PLANET_COLORS.length];
        const size = Math.random() * (PLANET_MAX_SIZE - PLANET_MIN_SIZE) + PLANET_MIN_SIZE;
        let ring = undefined;
        if (Math.random() < 0.25) { // Reduced chance of rings slightly as planets are smaller
          ring = {
            color: PLANET_RING_COLORS[i % PLANET_RING_COLORS.length],
            angle: Math.random() * Math.PI * 0.3 - Math.PI * 0.15, 
            width: size * (Math.random() * 0.25 + 0.15), // Adjusted ring width for smaller planets
            radiusFactor: Math.random() * 0.4 + 1.25, // Adjusted ring radius for smaller planets
          };
        }
        planetsRef.current.push({
          x: (Math.random() - 0.5) * virtualWidth * 0.98, // Spread them out more, closer to virtual edges
          y: (Math.random() - 0.5) * virtualHeight * 0.98, // Spread them out more
          size: size,
          baseColor: colorSet.base,
          detailColor: colorSet.detail,
          ring: ring,
        });
      }

      meteorsRef.current = [];
    };

    const preloadImages = () => {
      loadedCryptoImagesRef.current = [];
      cryptoLogoPaths.forEach(path => {
        const img = new Image();
        img.src = path;
        img.onload = () => { /* console.log(`Crypto logo loaded: ${path}`); */ };
        img.onerror = () => { console.error(`Failed to load crypto logo: ${path}`); };
        loadedCryptoImagesRef.current.push(img);
      });
    };

    const spawnMeteor = () => {
      let x, y, vx, vy;
      const speed = Math.random() * 2 + 1;
      const spawnType = Math.random(); // Determine spawn type: edge or fully random

      if (spawnType < 0.3) { // 30% chance to spawn from edge
        const edge = Math.floor(Math.random() * 4);
        const angleDeviation = (Math.random() - 0.5) * (Math.PI / 4);
        switch (edge) {
          case 0: 
            x = Math.random() * canvas.width;
            y = -20;
            vx = Math.sin(Math.PI / 2 + angleDeviation) * speed;
            vy = Math.cos(Math.PI / 2 + angleDeviation) * speed;
            break;
          case 1: 
            x = canvas.width + 20;
            y = Math.random() * canvas.height;
            vx = -Math.cos(angleDeviation) * speed;
            vy = Math.sin(angleDeviation) * speed;
            break;
          case 2: 
            x = Math.random() * canvas.width;
            y = canvas.height + 20;
            vx = Math.sin(-Math.PI / 2 + angleDeviation) * speed;
            vy = -Math.cos(-Math.PI / 2 + angleDeviation) * speed;
            break;
          default: 
            x = -20;
            y = Math.random() * canvas.height;
            vx = Math.cos(angleDeviation) * speed;
            vy = Math.sin(angleDeviation) * speed;
            break;
        }
      } else { // 70% chance to spawn randomly on screen with random direction
        x = Math.random() * canvas.width;
        y = Math.random() * canvas.height;
        const randomAngle = Math.random() * Math.PI * 2;
        vx = Math.cos(randomAngle) * speed;
        vy = Math.sin(randomAngle) * speed;
      }

      meteorsRef.current.push({
        x, y, vx, vy,
        length: Math.random() * 100 + 100,
        opacity: 0,
        maxOpacity: Math.random() * 0.3 + 0.7,
        life: 0,
        maxLife: 100 + Math.random() * 100,
        traveledDistance: 0,
        exploded: false,
        explosionParticles: [],
        explosionImage: null,
        explosionImageSize: null,
      });
    };

    const triggerExplosion = (meteorInstance: Meteor) => {
      meteorInstance.exploded = true;
      if (loadedCryptoImagesRef.current.length > 0) {
          const selectedImage = loadedCryptoImagesRef.current[Math.floor(Math.random() * loadedCryptoImagesRef.current.length)];
          if (selectedImage && selectedImage.complete && selectedImage.naturalHeight !== 0 && selectedImage.naturalWidth !== 0) {
              meteorInstance.explosionImage = selectedImage;
              const baseSize = Math.random() * 30 + 20;
              const aspectRatio = meteorInstance.explosionImage.naturalWidth / meteorInstance.explosionImage.naturalHeight;
              meteorInstance.explosionImageSize = {
                  width: baseSize * (aspectRatio >= 1 ? 1 : aspectRatio),
                  height: baseSize * (aspectRatio < 1 ? 1 : (1 / aspectRatio)),
              };
          } else {
            meteorInstance.explosionImage = null;
            meteorInstance.explosionImageSize = { width: 20, height: 20 };
          }
      } else {
        meteorInstance.explosionImage = null;
        meteorInstance.explosionImageSize = null;
      }

      for (let i = 0; i < explosionParticleCount; i++) {
          const angle = Math.random() * Math.PI * 2;
          const speed = Math.random() * explosionParticleSpeed + 0.5;
          meteorInstance.explosionParticles.push({
              x: meteorInstance.x,
              y: meteorInstance.y,
              vx: Math.cos(angle) * speed,
              vy: Math.sin(angle) * speed,
              size: Math.random() * 2 + 1,
              opacity: 1,
              life: 0,
              maxLife: explosionParticleDuration,
          });
      }
      meteorInstance.opacity = 0;
    };

    const handleMouseMove = (event: MouseEvent) => {
      mousePositionRef.current = { x: event.clientX, y: event.clientY };
    };

    const handleScroll = () => {
      scrollOffsetYRef.current = window.scrollY;
    };

    const animate = () => {
      const now = Date.now();
      if (now - lastMeteorSpawnTimeRef.current > meteorSpawnInterval * (0.5 + Math.random())) {
        spawnMeteor();
        lastMeteorSpawnTimeRef.current = now;
      }

      const dx = mousePositionRef.current.x - canvas.width / 2;
      const dy = mousePositionRef.current.y - canvas.height / 2;

      targetPanRef.current.x = Math.max(-panLimitX, Math.min(panLimitX, -dx * panSensitivity));
      
      // Combine mouse and scroll panning for Y axis
      const mouseDrivenOffsetY = -dy * panSensitivity;
      const scrollDrivenOffsetY = -scrollOffsetYRef.current * scrollPanSensitivity;
      const combinedOffsetY = mouseDrivenOffsetY + scrollDrivenOffsetY;
      targetPanRef.current.y = Math.max(-panLimitY, Math.min(panLimitY, combinedOffsetY));
      
      currentPanRef.current.x += (targetPanRef.current.x - currentPanRef.current.x) * panEasing;
      currentPanRef.current.y += (targetPanRef.current.y - currentPanRef.current.y) * panEasing;

      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      ctx.save();
      ctx.translate(canvas.width / 2 + currentPanRef.current.x, canvas.height / 2 + currentPanRef.current.y);

      // Draw Stars
      starsRef.current.forEach(star => {
        ctx.beginPath();
        ctx.arc(star.x, star.y, star.size, 0, Math.PI * 2);
        ctx.fillStyle = starColor.replace(/,\s*([\d.]+)\)/, `, ${star.opacity})`);
        ctx.fill();
      });

      // Draw Planets
      planetsRef.current.forEach(planet => {
        ctx.beginPath();
        if (planet.detailColor) {
          const gradient = ctx.createRadialGradient(planet.x, planet.y, planet.size * 0.2, planet.x, planet.y, planet.size);
          gradient.addColorStop(0, planet.detailColor);
          gradient.addColorStop(1, planet.baseColor);
          ctx.fillStyle = gradient;
        } else {
          ctx.fillStyle = planet.baseColor;
        }
        ctx.arc(planet.x, planet.y, planet.size, 0, Math.PI * 2);
        ctx.fill();

        if (planet.ring) {
          ctx.beginPath();
          ctx.strokeStyle = planet.ring.color;
          ctx.lineWidth = planet.ring.width;
          // Drawing rings as an ellipse (scaled circle)
          ctx.save();
          ctx.translate(planet.x, planet.y);
          ctx.rotate(planet.ring.angle);
          ctx.scale(1, 0.3); // Scale Y to make it look like a ring seen from an angle
          ctx.arc(0, 0, planet.size * planet.ring.radiusFactor, 0, Math.PI * 2);
          ctx.restore();
          ctx.stroke();
        }
      });

      ctx.restore(); // Restore from star/planet panning context

      // Meteors are drawn in a separate context (not panned with stars/planets)
      meteorsRef.current = meteorsRef.current.filter(meteor => {
        if (!meteor.exploded) {
          meteor.x += meteor.vx;
          meteor.y += meteor.vy;
          meteor.traveledDistance += Math.sqrt(meteor.vx**2 + meteor.vy**2);
          meteor.life++;

          if (meteor.life < meteor.maxLife / 2) {
            meteor.opacity = (meteor.life / (meteor.maxLife / 2)) * meteor.maxOpacity;
          } else {
            meteor.opacity = (1 - (meteor.life - meteor.maxLife / 2) / (meteor.maxLife / 2)) * meteor.maxOpacity;
          }

          if (meteor.opacity <= 0 || meteor.life >= meteor.maxLife) {
            if (meteor.explosionParticles.length === 0) return false;
          }

          if (!meteor.exploded && meteor.traveledDistance > meteorExplosionDistance) {
            triggerExplosion(meteor);
          }

          if (!meteor.exploded) {
            const centerX = canvas.width / 2;
            const horizontalCenterBand = canvas.width / 3;
            const minX = centerX - horizontalCenterBand / 2;
            const maxX = centerX + horizontalCenterBand / 2;
            
            const verticalTolerance = canvas.height / 4;
            const minY = canvas.height / 2 - verticalTolerance;
            const maxY = canvas.height / 2 + verticalTolerance;

            const minTravelForCentral = meteorExplosionDistance * 0.4;

            if (meteor.x > minX && meteor.x < maxX && 
                meteor.y > minY && meteor.y < maxY && 
                meteor.traveledDistance > minTravelForCentral) {
                if (Math.random() < 0.6) { 
                     triggerExplosion(meteor);
                }
            }
          }
        }

        if (meteor.exploded) {
          meteor.explosionParticles.forEach(p => {
            p.x += p.vx;
            p.y += p.vy;
            p.life++;
            p.opacity = 1 - (p.life / p.maxLife);
          });

          meteor.explosionParticles = meteor.explosionParticles.filter(p => p.opacity > 0 && p.life < p.maxLife);

          meteor.explosionParticles.forEach(p => {
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
            const particleColorMatch = meteorColor.match(/(rgba?\([^,]+,[^,]+,[^,]+)/);
            const particleBaseColor = particleColorMatch ? particleColorMatch[1] : 'rgba(255,255,255)';
            ctx.fillStyle = `${particleBaseColor},${p.opacity})`;
            ctx.fill();
          });
          
          if (meteor.explosionImage && meteor.explosionImageSize && meteor.explosionParticles.length > 0) {
            if (meteor.explosionImage.complete && meteor.explosionImage.naturalHeight !== 0) { 
                const imageOpacity = meteor.explosionParticles[0] ? meteor.explosionParticles[0].opacity * 0.9 : 0.9;
                ctx.save();
                ctx.globalAlpha = imageOpacity > 0 ? imageOpacity : 0;
                const imgWidth = meteor.explosionImageSize.width;
                const imgHeight = meteor.explosionImageSize.height;
                ctx.drawImage(meteor.explosionImage, meteor.x - imgWidth / 2, meteor.y - imgHeight / 2, imgWidth, imgHeight);
                ctx.restore();
            }
          }
          
          if (meteor.explosionParticles.length === 0) return false;
        }

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
          ctx.lineWidth = 2.5;
          ctx.stroke();
        }
        
        return true;
      });

      animationFrameIdRef.current = requestAnimationFrame(animate);
    };

    initializeStarsAndCanvas();
    preloadImages();
    window.addEventListener('resize', () => {
        initializeStarsAndCanvas();
        preloadImages();
    });
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('scroll', handleScroll);
    
    // Initialize scroll position once
    handleScroll();

    animate();

    return () => {
      window.removeEventListener('resize', initializeStarsAndCanvas);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('scroll', handleScroll);
      if (animationFrameIdRef.current) {
        cancelAnimationFrame(animationFrameIdRef.current);
      }
    };
  }, [starCount, starColor, starSizeMultiplier, starOpacityBase, panSensitivity, panEasing, virtualSizeMultiplier, meteorSpawnInterval, meteorColor, meteorExplosionDistance, explosionParticleCount, explosionParticleSpeed, explosionParticleDuration, cryptoLogoPaths, planetCount, scrollPanSensitivity]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        zIndex: -1,
        background: 'radial-gradient(ellipse at bottom, #0d1a26 0%, #040608 100%)',
      }}
    />
  );
};

export { InteractiveStarryBackground }; 