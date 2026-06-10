interface LogoProps {
  size?: number;
  className?: string;
}

export function Logo({ size = 28, className = "" }: LogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      className={className}
      aria-hidden
    >
      <path
        d="M16 2L28 9v14l-12 7L4 23V9L16 2z"
        stroke="currentColor"
        strokeWidth="1.5"
        fill="rgba(59, 130, 246, 0.15)"
      />
      <path
        d="M16 8l6 3.5v7L16 22l-6-3.5v-7L16 8z"
        stroke="currentColor"
        strokeWidth="1.2"
        fill="rgba(6, 182, 212, 0.2)"
      />
      <circle cx="16" cy="15" r="2" fill="currentColor" />
    </svg>
  );
}
