/**
 * AnimatedPage — framer-motion removed; replaced with plain passthrough wrappers.
 * Page transitions are handled by CSS (Tailwind transition utilities) as needed.
 */

export const pageVariants = {};
export const pageTransition = {};

export const AnimatedPage = ({ children, className = "" }) => (
    <div className={className}>{children}</div>
);

export const FadeIn = ({ children }) => (
    <div>{children}</div>
);

export const SlideIn = ({ children }) => (
    <div>{children}</div>
);

export const ScaleIn = ({ children }) => (
    <div>{children}</div>
);

export const StaggerContainer = ({ children }) => (
    <div>{children}</div>
);

export const StaggerItem = ({ children }) => (
    <div>{children}</div>
);

export default AnimatedPage;
