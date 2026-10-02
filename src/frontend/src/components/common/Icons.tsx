import React from 'react';

interface IconProps {
  className?: string;
  size?: number | string;
  color?: string;
}

/**
 * FontAwesome-styled SVG Vector Icons (No emoji).
 */

export const GearIcon: React.FC<IconProps> = ({ className, size = 15, color = 'currentColor' }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 512 512"
    fill={color}
    className={className}
    aria-hidden="true"
  >
    {/* FontAwesome fa-gear / fa-cog */}
    <path d="M495.9 166.6c3.2 8.7 .5 18.4-6.4 24.6l-43.3 39.4c1.1 8.3 1.7 16.8 1.7 25.4s-.6 17.1-1.7 25.4l43.3 39.4c6.9 6.2 9.6 15.9 6.4 24.6c-4.4 11.9-9.7 23.3-15.8 34.3l-4.7 8.1c-6.6 11-14 21.4-22.1 31.2c-5.9 7.2-15.7 9.6-24.5 6.8l-55.7-17.7c-13.4 10.3-28.2 18.9-44 25.4l-12.5 57.1c-2 9.1-9 16.3-18.2 17.8c-13.8 2.3-28 3.5-42.5 3.5s-28.7-1.2-42.5-3.5c-9.2-1.5-16.2-8.7-18.2-17.8l-12.5-57.1c-15.8-6.5-30.6-15.1-44-25.4L83.1 425.9c-8.8 2.8-18.6 .3-24.5-6.8c-8.1-9.8-15.5-20.2-22.1-31.2l-4.7-8.1c-6.1-11-11.4-22.4-15.8-34.3c-3.2-8.7-.5-18.4 6.4-24.6l43.3-39.4C64.6 273.1 64 264.6 64 256s.6-17.1 1.7-25.4L22.4 191.2c-6.9-6.2-9.6-15.9-6.4-24.6c4.4-11.9 9.7-23.3 15.8-34.3l4.7-8.1c6.6-11 14-21.4 22.1-31.2c5.9-7.2 15.7-9.6 24.5-6.8l55.7 17.7c13.4-10.3 28.2-18.9 44-25.4l12.5-57.1c2-9.1 9-16.3 18.2-17.8C227.3 65.2 241.5 64 256 64s28.7 1.2 42.5 3.5c9.2 1.5 16.2 8.7 18.2 17.8l12.5 57.1c15.8 6.5 30.6 15.1 44 25.4l55.7-17.7c8.8-2.8 18.6-.3 24.5 6.8c8.1 9.8 15.5 20.2 22.1 31.2l4.7 8.1c6.1 11 11.4 22.4 15.8 34.3zM256 336a80 80 0 1 0 0-160 80 80 0 1 0 0 160z" />
  </svg>
);

export const MathSymbolsIcon: React.FC<IconProps> = ({ className, size = 16, color = 'currentColor' }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke={color}
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
    aria-hidden="true"
  >
    {/* Integral & Sigma symbol */}
    <path d="M7 4c-1.5 0-3 1.2-3 3v10c0 1.8 1.5 3 3 3" />
    <path d="M14 6h6l-4 6 4 6h-6" />
    <path d="M10 12h2" />
  </svg>
);

export const CameraIcon: React.FC<IconProps> = ({ className, size = 15, color = 'currentColor' }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 512 512"
    fill={color}
    className={className}
    aria-hidden="true"
  >
    {/* FontAwesome fa-camera */}
    <path d="M149.1 64.8L138.7 96H64C28.7 96 0 124.7 0 160V416c0 35.3 28.7 64 64 64H448c35.3 0 64-28.7 64-64V160c0-35.3-28.7-64-64-64H373.3L362.9 64.8C356.4 45.2 338.1 32 317.4 32H194.6c-20.7 0-39 13.2-45.5 32.8zM256 192a96 96 0 1 1 0 192 96 96 0 1 1 0-192z" />
  </svg>
);

export const StarIcon: React.FC<IconProps> = ({ className, size = 14, color = 'currentColor' }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 576 512"
    fill={color}
    className={className}
    aria-hidden="true"
  >
    {/* FontAwesome fa-star */}
    <path d="M316.9 18C311.6 7 300.4 0 288.1 0s-23.6 7-28.8 18L195 150.3 51.4 171.5c-12 1.8-22 10.2-25.7 21.7s-.7 24.2 7.9 32.7L137.8 329 113.2 474.7c-2 12 3 24.2 12.9 31.3s23 8 33.8 2.3l128.3-68.5 128.3 68.5c10.8 5.7 23.9 4.9 33.8-2.3s14.9-19.3 12.9-31.3L438.5 329 542.7 225.9c8.6-8.5 11.7-21.2 7.9-32.7s-13.7-19.9-25.7-21.7L381.2 150.3 316.9 18z" />
  </svg>
);

export const SquareRootIcon: React.FC<IconProps> = ({ className, size = 15, color = 'currentColor' }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke={color}
    strokeWidth="2.2"
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
    aria-hidden="true"
  >
    {/* Radical / Square root vector */}
    <path d="M3 13l3 7 5-15h10" />
  </svg>
);

export const CalculusIcon: React.FC<IconProps> = ({ className, size = 15, color = 'currentColor' }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke={color}
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
    aria-hidden="true"
  >
    {/* ∂∫ partial + integral */}
    <path d="M8 12a3 3 0 1 0 0 6h1a4 4 0 0 0 4-4V6a3 3 0 0 0-3-3" />
    <path d="M19 4c-1.5 0-3 1.2-3 3v10c0 1.8 1.5 3 3 3" />
  </svg>
);

export const MatrixIcon: React.FC<IconProps> = ({ className, size = 15, color = 'currentColor' }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke={color}
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
    aria-hidden="true"
  >
    {/* Matrix brackets (::) */}
    <path d="M5 4v16M19 4v16" />
    <circle cx="9" cy="8" r="1" fill={color} />
    <circle cx="15" cy="8" r="1" fill={color} />
    <circle cx="9" cy="16" r="1" fill={color} />
    <circle cx="15" cy="16" r="1" fill={color} />
  </svg>
);

export const WaveIcon: React.FC<IconProps> = ({ className, size = 15, color = 'currentColor' }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke={color}
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
    aria-hidden="true"
  >
    {/* Sine wave ∿ */}
    <path d="M2 12c2.5-5 5.5-5 8 0s5.5 5 8 0 4-3 4-3" />
  </svg>
);

export const GreekIcon: React.FC<IconProps> = ({ className, size = 15, color = 'currentColor' }) => (
  <span
    style={{
      fontSize: size,
      fontWeight: 'bold',
      fontFamily: 'serif',
      color: color,
      lineHeight: 1,
      userSelect: 'none',
    }}
    className={className}
    aria-hidden="true"
  >
    α<sub>ω</sub>
  </span>
);

export const EllipsisIcon: React.FC<IconProps> = ({ className, size = 15, color = 'currentColor' }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 512 512"
    fill={color}
    className={className}
    aria-hidden="true"
  >
    {/* FontAwesome fa-ellipsis */}
    <path d="M64 304a48 48 0 1 0 0-96 48 48 0 1 0 0 96zm192 0a48 48 0 1 0 0-96 48 48 0 1 0 0 96zm192 0a48 48 0 1 0 0-96 48 48 0 1 0 0 96z" />
  </svg>
);

export const KeyboardIcon: React.FC<IconProps> = ({ className, size = 15, color = 'currentColor' }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 576 512"
    fill={color}
    className={className}
    aria-hidden="true"
  >
    {/* FontAwesome fa-keyboard */}
    <path d="M64 64C28.7 64 0 92.7 0 128V384c0 35.3 28.7 64 64 64H512c35.3 0 64-28.7 64-64V128c0-35.3-28.7-64-64-64H64zm64 96a32 32 0 1 1 0 64 32 32 0 1 1 0-64zm96 0a32 32 0 1 1 0 64 32 32 0 1 1 0-64zm96 0a32 32 0 1 1 0 64 32 32 0 1 1 0-64zm96 0a32 32 0 1 1 0 64 32 32 0 1 1 0-64zM96 288a32 32 0 1 1 64 0 32 32 0 1 1 -64 0zm96 0a32 32 0 1 1 64 0 32 32 0 1 1 -64 0zm96 0a32 32 0 1 1 64 0 32 32 0 1 1 -64 0zm96 0a32 32 0 1 1 64 0 32 32 0 1 1 -64 0zM160 384c-17.7 0-32-14.3-32-32s14.3-32 32-32H416c17.7 0 32 14.3 32 32s-14.3 32-32 32H160z" />
  </svg>
);

export const GridIcon: React.FC<IconProps> = ({ className, size = 15, color = 'currentColor' }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 448 512"
    fill={color}
    className={className}
    aria-hidden="true"
  >
    {/* FontAwesome fa-table-cells */}
    <path d="M64 32C28.7 32 0 60.7 0 96V416c0 35.3 28.7 64 64 64H384c35.3 0 64-28.7 64-64V96c0-35.3-28.7-64-64-64H64zm80 96V224H64V128h80zm48 0H304V224H192V128zm160 0h32c8.8 0 16 7.2 16 16v80H352V128zM64 272h80v96H64V272zm128 0H304v96H192V272zm160 0h48v96H352V272z" />
  </svg>
);

export const UploadIcon: React.FC<IconProps> = ({ className, size = 15, color = 'currentColor' }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 512 512"
    fill={color}
    className={className}
    aria-hidden="true"
  >
    {/* FontAwesome fa-upload */}
    <path d="M288 109.3V352c0 17.7-14.3 32-32 32s-32-14.3-32-32V109.3l-73.4 73.4c-12.5 12.5-32.8 12.5-45.3 0s-12.5-32.8 0-45.3l128-128c12.5-12.5 32.8-12.5 45.3 0l128 128c12.5 12.5 12.5 32.8 0 45.3s-32.8 12.5-45.3 0L288 109.3zM64 352H192c0 35.3 28.7 64 64 64s64-28.7 64-64H448c35.3 0 64 28.7 64 64v32c0 35.3-28.7 64-64 64H64c-35.3 0-64-28.7-64-64V416c0-35.3 28.7-64 64-64zM432 456a24 24 0 1 0 0-48 24 24 0 1 0 0 48z" />
  </svg>
);

export const ShuffleIcon: React.FC<IconProps> = ({ className, size = 15, color = 'currentColor' }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 512 512"
    fill={color}
    className={className}
    aria-hidden="true"
  >
    {/* FontAwesome fa-shuffle */}
    <path d="M403.8 34.4c12-5 25.7-2.2 34.9 6.9l64 64c6 6 9.4 14.1 9.4 22.6s-3.4 16.6-9.4 22.6l-64 64c-9.2 9.2-22.9 11.9-34.9 6.9s-19.8-16.6-19.8-29.6V160H352c-10.1 0-19.6 4.7-25.6 12.8L284 232.9 224 313.1c-17.9 24.1-46.3 38.3-76.6 38.3H32c-17.7 0-32-14.3-32-32s14.3-32 32-32H147.4c10.1 0 19.6-4.7 25.6-12.8L233 207.1 293 126.9c17.9-24.1 46.3-38.3 76.6-38.3h14.4V56c0-13 7.8-24.6 19.8-29.6zM147.4 160H32c-17.7 0-32-14.3-32-32s14.3-32 32-32H147.4c30.3 0 58.7 14.2 76.6 38.3l27.1 36.4-38.4 51.2-24.7-33.1c-6-8.1-15.5-12.8-25.6-12.8zM403.8 322.4c12-5 25.7-2.2 34.9 6.9l64 64c6 6 9.4 14.1 9.4 22.6s-3.4 16.6-9.4 22.6l-64 64c-9.2 9.2-22.9 11.9-34.9 6.9s-19.8-16.6-19.8-29.6V448H369.6c-30.3 0-58.7-14.2-76.6-38.3L265.9 373.3l38.4-51.2 24.7 33.1c6 8.1 15.5 12.8 25.6 12.8H384V336c0-13 7.8-24.6 19.8-29.6z" />
  </svg>
);

export const TimesCircleIcon: React.FC<IconProps> = ({ className, size = 18, color = 'currentColor' }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 512 512"
    fill={color}
    className={className}
    aria-hidden="true"
  >
    {/* FontAwesome fa-circle-xmark */}
    <path d="M256 512A256 256 0 1 0 256 0a256 256 0 1 0 0 512zM175 175c9.4-9.4 24.6-9.4 33.9 0l47 47 47-47c9.4-9.4 24.6-9.4 33.9 0s9.4 24.6 0 33.9l-47 47 47 47c9.4 9.4 9.4 24.6 0 33.9s-24.6 9.4-33.9 0l-47-47-47 47c-9.4 9.4-24.6 9.4-33.9 0s-9.4-24.6 0-33.9l47-47-47-47c-9.4-9.4-9.4-24.6 0-33.9z" />
  </svg>
);

export const EqualsIcon: React.FC<IconProps> = ({ className, size = 18, color = 'currentColor' }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 448 512"
    fill={color}
    className={className}
    aria-hidden="true"
  >
    {/* FontAwesome fa-equals */}
    <path d="M48 128c-17.7 0-32 14.3-32 32s14.3 32 32 32l352 0c17.7 0 32-14.3 32-32s-14.3-32-32-32L48 128zm0 192c-17.7 0-32 14.3-32 32s14.3 32 32 32l352 0c17.7 0 32-14.3 32-32s-14.3-32-32-32L48 320z" />
  </svg>
);
