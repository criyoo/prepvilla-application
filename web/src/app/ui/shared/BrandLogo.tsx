"use client";

interface BrandLogoProps {
  alt?: string;
  className?: string;
}

export default function BrandLogo({ alt = "PrepVilla", className = "" }: BrandLogoProps) {
  return (
    <img
      src="/logo/logo_v9.png"
      alt={alt}
      draggable={false}
      onDragStart={(event) => event.preventDefault()}
      className={`object-contain select-none ${className}`}
    />
  );
}