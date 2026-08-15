/**
 * Icon — PNG 图标（与 PhiAgent 同源视觉）
 * <Icon name="icon-search" size={16} />
 */
export default function Icon({ name, size = 20, style, className, ...props }) {
  return (
    <img
      src={`/icons/${name}.png`}
      alt=""
      loading="lazy"
      width={size}
      height={size}
      {...props}
      className={`icon-img${className ? ' ' + className : ''}`}
      style={{
        width: size,
        height: size,
        display: 'inline-block',
        verticalAlign: 'middle',
        flexShrink: 0,
        ...style,
      }}
    />
  );
}
