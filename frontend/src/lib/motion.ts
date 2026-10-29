/** Shared motion tokens. CSS counterparts live in styles/index.css (--dur-*, --ease). */
export const spring = { soft: { type: "spring", stiffness: 420, damping: 38, mass: 0.9 }, snappy: { type: "spring", stiffness: 560, damping: 40 } } as const;
export const ease = [0.2, 0.8, 0.2, 1] as const;
export const dur = { fast: 0.14, base: 0.22, slow: 0.34 } as const;
export const fade = { initial: { opacity: 0 }, animate: { opacity: 1 }, exit: { opacity: 0 }, transition: { duration: dur.base, ease } } as const;
export const press = { whileTap: { scale: 0.94 }, transition: spring.snappy } as const;
