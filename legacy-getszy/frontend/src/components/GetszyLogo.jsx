export function GetszyLogo({ className = "", size = "default", dark = false }) {
  const sizes = {
    sm: { width: 100, height: 24 },
    default: { width: 140, height: 34 },
    lg: { width: 200, height: 48 },
  };
  const { width, height } = sizes[size] || sizes.default;
  const textColor = dark ? "#FBF7F2" : "#2D2D2D";

  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 48" fill="none" width={width} height={height} className={className}>
      <defs>
        <linearGradient id={`rg-${size}`} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#C58B7A"/>
          <stop offset="50%" stopColor="#D4A08F"/>
          <stop offset="100%" stopColor="#B87A6A"/>
        </linearGradient>
        <linearGradient id={`tl-${size}`} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#2F7E7A"/>
          <stop offset="100%" stopColor="#3A9E99"/>
        </linearGradient>
      </defs>
      <path d="M8 24 L12 16 L16 24 L12 32 Z" fill={`url(#tl-${size})`} opacity="0.9"/>
      <circle cx="12" cy="12" r="2" fill={`url(#tl-${size})`} opacity="0.6"/>
      <circle cx="20" cy="20" r="1.5" fill={`url(#rg-${size})`} opacity="0.5"/>
      <text x="32" y="34" fontFamily="Georgia, 'Times New Roman', serif" fontSize="36" fontWeight="400" letterSpacing="-1" fill={textColor}>getszy</text>
    </svg>
  );
}

export function GetszyIcon({ className = "", size = 32 }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" fill="none" width={size} height={size} className={className}>
      <defs>
        <linearGradient id="bgIcon" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#FBF7F2"/>
          <stop offset="100%" stopColor="#F5E6D3"/>
        </linearGradient>
        <linearGradient id="rgI" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#C58B7A"/>
          <stop offset="100%" stopColor="#B87A6A"/>
        </linearGradient>
        <linearGradient id="tlI" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#2F7E7A"/>
          <stop offset="100%" stopColor="#3A9E99"/>
        </linearGradient>
      </defs>
      <rect x="2" y="2" width="60" height="60" rx="14" fill="url(#bgIcon)" stroke="url(#rgI)" strokeWidth="2"/>
      <text x="32" y="44" textAnchor="middle" fontFamily="Georgia, serif" fontSize="38" fontWeight="400" fill="url(#rgI)">g</text>
      <path d="M48 12 L50 8 L52 12 L56 14 L52 16 L50 20 L48 16 L44 14 Z" fill="url(#tlI)" opacity="0.8"/>
      <circle cx="50" cy="8" r="1.5" fill="url(#tlI)" opacity="0.5"/>
    </svg>
  );
}