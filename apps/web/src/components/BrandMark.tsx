/** Shared, monochrome SVG brand mark. Decorative beside the product name. */
export function BrandMark() {
  return (
    <svg
      className="brand-mark"
      width="28"
      height="28"
      viewBox="0 0 64 64"
      fill="none"
      aria-hidden="true"
    >
      <rect
        x="16"
        y="16"
        width="32"
        height="32"
        rx="10"
        transform="rotate(45 32 32)"
        stroke="currentColor"
        strokeWidth="5"
      />
    </svg>
  );
}
