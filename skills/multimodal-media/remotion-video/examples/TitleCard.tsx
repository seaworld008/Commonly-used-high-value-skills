import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';

// Original example. Register it in the user's existing composition root.
export const TitleCard: React.FC<{title: string}> = ({title}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const fadeFrames = Math.max(1, Math.min(Math.round(fps / 2), durationInFrames - 1));
  const opacity = durationInFrames <= 1 ? 1 : interpolate(frame, [0, fadeFrames], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  return (
    <AbsoluteFill style={{background: '#101828', color: '#fff', justifyContent: 'center', alignItems: 'center'}}>
      <div style={{opacity, fontSize: 64, padding: 48, textAlign: 'center'}}>{title}</div>
    </AbsoluteFill>
  );
};
