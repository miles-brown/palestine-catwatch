import PropTypes from 'prop-types';

/**
 * Palestine solidarity ribbon in the style of awareness ribbons.
 * Uses the four colors of the Palestinian flag: black, white, green, and red.
 * @param {Object} props - Component props
 * @param {string} props.size - Size variant: 'sm', 'md', or 'lg'
 * @param {string} props.className - Additional CSS classes
 * @returns {JSX.Element} SVG ribbon element
 */
const PalestineRibbon = ({ size = 'md', className = '' }) => {
  const sizes = {
    sm: { width: 20, height: 28 },
    md: { width: 28, height: 40 },
    lg: { width: 40, height: 56 },
  };

  const { width, height } = sizes[size] || sizes.md;

  return (
    <svg
      width={width}
      height={height}
      viewBox="0 0 40 56"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      role="img"
      aria-label="Palestine solidarity ribbon"
    >
      {/* Left ribbon tail - Black */}
      <path
        d="M8 0C8 0 4 8 4 16C4 24 8 32 12 40C14 44 15 48 14 56L20 48L18 40C16 32 14 24 14 16C14 8 16 4 18 0H8Z"
        fill="#000000"
      />

      {/* Left ribbon highlight - White */}
      <path
        d="M14 0C14 0 12 8 12 16C12 20 13 24 14 28L16 24C15 20 14 16 14 12C14 8 15 4 16 0H14Z"
        fill="#FFFFFF"
        opacity="0.9"
      />

      {/* Right ribbon tail - Green */}
      <path
        d="M32 0C32 0 36 8 36 16C36 24 32 32 28 40C26 44 25 48 26 56L20 48L22 40C24 32 26 24 26 16C26 8 24 4 22 0H32Z"
        fill="#007A3D"
      />

      {/* Right ribbon highlight - lighter green */}
      <path
        d="M26 0C26 0 28 8 28 16C28 20 27 24 26 28L24 24C25 20 26 16 26 12C26 8 25 4 24 0H26Z"
        fill="#00A651"
        opacity="0.6"
      />

      {/* Center knot/fold - Red triangle inspired */}
      <path
        d="M14 16L20 8L26 16L22 20H18L14 16Z"
        fill="#CE1126"
      />

      {/* Knot shadow */}
      <path
        d="M18 20H22L20 24L18 20Z"
        fill="#9E0D1B"
      />

      {/* White accent on knot */}
      <path
        d="M18 14L20 10L22 14L20 16L18 14Z"
        fill="#FFFFFF"
        opacity="0.4"
      />
    </svg>
  );
};

PalestineRibbon.propTypes = {
  size: PropTypes.oneOf(['sm', 'md', 'lg']),
  className: PropTypes.string,
};

export default PalestineRibbon;
