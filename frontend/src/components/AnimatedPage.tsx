import React from 'react';

/**
 * AnimatedPage — framer-motion removed; replaced with plain passthrough wrappers.
 * Page transitions are handled by CSS (Tailwind transition utilities) as needed.
 */

export const pageVariants = {};
export const pageTransition = {};

interface AnimatedProps {
    children: React.ReactNode;
    className?: string;
    variants?: any;
    transition?: any;
}

export const AnimatedPage: React.FC<AnimatedProps> = ({ children, className = "" }) => (
    <div className={className}>{children}</div>
);

export const FadeIn: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <div>{children}</div>
);

export const SlideIn: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <div>{children}</div>
);

export const ScaleIn: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <div>{children}</div>
);

export const StaggerContainer: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <div>{children}</div>
);

export const StaggerItem: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <div>{children}</div>
);

export default AnimatedPage;
