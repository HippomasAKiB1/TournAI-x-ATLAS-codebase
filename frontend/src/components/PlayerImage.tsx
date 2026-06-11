"use client";

import React, { useState, useEffect } from "react";
import { User } from "lucide-react";

interface PlayerImageProps {
  playerName: string;
  className?: string;
  fallbackSize?: number;
}

// Global memory cache to avoid duplicate fetches during session
const playerImageCache: Record<string, string> = {};

export default function PlayerImage({ playerName, className = "", fallbackSize = 24 }: PlayerImageProps) {
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!playerName) {
      setLoading(false);
      setImageUrl(null);
      return;
    }

    // Check memory cache
    if (playerImageCache[playerName]) {
      setImageUrl(playerImageCache[playerName]);
      setLoading(false);
      return;
    }

    // Check localStorage cache
    const cacheKey = `player_img_v1_${playerName}`;
    const cached = localStorage.getItem(cacheKey);
    if (cached) {
      playerImageCache[playerName] = cached;
      setImageUrl(cached);
      setLoading(false);
      return;
    }

    let active = true;
    const fetchImage = async () => {
      try {
        // Standardize name for Wikipedia search query
        const cleanName = playerName.replace(/\b(GK|DEF|MID|FWD)\b/gi, "").trim();
        const url = `https://en.wikipedia.org/w/api.php?action=query&titles=${encodeURIComponent(
          cleanName
        )}&prop=pageimages&format=json&pithumbsize=200&origin=*`;

        const res = await fetch(url);
        if (res.ok) {
          const data = await res.json();
          const pages = data.query?.pages;
          if (pages) {
            const pageInfo = Object.values(pages)[0] as any;
            const sourceUrl = pageInfo.thumbnail?.source;
            if (sourceUrl && active) {
              playerImageCache[playerName] = sourceUrl;
              localStorage.setItem(cacheKey, sourceUrl);
              setImageUrl(sourceUrl);
            }
          }
        }
      } catch (err) {
        console.warn(`Failed to resolve player headshot for ${playerName}:`, err);
      } finally {
        if (active) setLoading(false);
      }
    };

    fetchImage();

    return () => {
      active = false;
    };
  }, [playerName]);

  const getInitials = (name: string) => {
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .substring(0, 2)
      .toUpperCase();
  };

  if (loading) {
    return (
      <div className={`flex items-center justify-center bg-zinc-900 rounded-full animate-pulse shrink-0 ${className}`}>
        <User size={fallbackSize} className="text-zinc-700" />
      </div>
    );
  }

  if (imageUrl) {
    return (
      <img
        src={imageUrl}
        alt={playerName}
        className={`object-cover rounded-full aspect-square shrink-0 ${className}`}
        onError={() => setImageUrl(null)}
      />
    );
  }

  return (
    <div className={`flex items-center justify-center bg-gradient-to-br from-purple-600/30 to-indigo-500/30 border border-purple-500/25 rounded-full text-white font-bold select-none shrink-0 ${className}`}>
      <span style={{ fontSize: `${fallbackSize * 0.45}px` }}>{getInitials(playerName)}</span>
    </div>
  );
}
