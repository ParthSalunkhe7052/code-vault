import { motion, AnimatePresence } from 'framer-motion';
import { useLocation } from 'react-router-dom';

export const pageVariants = {
    initial: {
        opacity: 0,
        y: 20,
    },
    animate: {
        opacity: 1,
        y: 0,
    },
    exit: {
        opacity: 0,
        y: -20,
    },
};

export const pageTransition = {
    duration: 0.3,
    ease: [0.4, 0, 0.2, 1], // Ease out
};

export const AnimatedPage = ({
    children,
    className = "",
    variants = pageVariants,
    transition = pageTransition,
}) => {
    const location = useLocation();

    return (
        <AnimatePresence mode="wait">
            <motion.div
                key={location.pathname}
                initial="initial"
                animate="animate"
                exit="exit"
                variants={variants}
                transition={transition}
                className={className}
            >
                {children}
            </motion.div>
        </AnimatePresence>
    );
};

export const FadeIn = ({ children, delay = 0, duration = 0.5 }) => (
    <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration, delay, ease: [0.4, 0, 0.2, 1] }}
    >
        {children}
    </motion.div>
);

export const SlideIn = ({ children, direction = 'left', delay = 0 }) => {
    const directions = {
        left: { x: -50, y: 0 },
        right: { x: 50, y: 0 },
        up: { x: 0, y: -50 },
        down: { x: 0, y: 50 },
    };

    return (
        <motion.div
            initial={{ opacity: 0, ...directions[direction] }}
            animate={{ opacity: 1, x: 0, y: 0 }}
            transition={{ duration: 0.5, delay, ease: [0.4, 0, 0.2, 1] }}
        >
            {children}
        </motion.div>
    );
};

export const ScaleIn = ({ children, delay = 0 }) => (
    <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4, delay, ease: [0.4, 0, 0.2, 1] }}
    >
        {children}
    </motion.div>
);

export const StaggerContainer = ({ children, staggerDelay = 0.1 }) => (
    <motion.div
        initial="initial"
        animate="animate"
        variants={{
            animate: {
                transition: {
                    staggerChildren: staggerDelay,
                },
            },
        }}
    >
        {children}
    </motion.div>
);

export const StaggerItem = ({ children }) => (
    <motion.div
        variants={{
            initial: { opacity: 0, y: 20 },
            animate: { opacity: 1, y: 0 },
        }}
        transition={{ duration: 0.4, ease: [0.4, 0, 0.2, 1] }}
    >
        {children}
    </motion.div>
);

export default AnimatedPage;
