"use client";

import { useState } from "react";
import { GripVertical } from "lucide-react";

interface ResizeHandleProps {
  onResize: (deltaX: number) => void;
  className?: string;
}

export function ResizeHandle({ onResize, className = "" }: ResizeHandleProps) {
  const [isDragging, setIsDragging] = useState(false);

  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);

    let lastX = e.clientX;

    const handleMouseMove = (moveEvent: MouseEvent) => {
      const deltaX = moveEvent.clientX - lastX;
      lastX = moveEvent.clientX;
      onResize(deltaX);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  };

  return (
    <div
      className={`group relative w-1 hover:w-1.5 transition-all cursor-col-resize flex items-center justify-center ${
        isDragging ? "bg-blue-400" : "bg-zinc-800 hover:bg-zinc-700"
      } ${className}`}
      onMouseDown={handleMouseDown}
    >
      <div
        className={`absolute inset-y-0 -left-1 -right-1 flex items-center justify-center ${
          isDragging ? "opacity-100" : "opacity-0 group-hover:opacity-100"
        } transition-opacity`}
      >
        <GripVertical
          className={`w-4 h-4 ${
            isDragging ? "text-blue-400" : "text-zinc-600"
          }`}
        />
      </div>
    </div>
  );
}
