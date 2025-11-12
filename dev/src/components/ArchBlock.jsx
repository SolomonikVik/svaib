import * as Icons from 'lucide-react';

export default function ArchBlock({ block, onClick }) {
  const Icon = Icons[block.icon];

  // Размеры блоков
  const sizeClasses = {
    'central-large': 'w-[356px] h-[187px]',  // Центральные: +20% (привлекают внимание)
    'data-square': 'w-[176px] h-[192px]',    // Блоки данных: вертикально вытянутые
    'ai-wide': 'w-[760px] h-[130px]'         // AI-слой: широкий, от края до края
  };

  // Стили по категориям
  const categoryStyles = {
    central: 'bg-white border-2 border-primary',
    data: 'bg-white border-2 border-primary',
    processing: 'gradient-cta text-white'
  };

  // Специальный стиль для центральных блоков с градиентной рамкой и индивидуальным фоном
  const centralGradientStyle = block.category === 'central' ? {
    background: block.id === 'presentation'
      ? 'linear-gradient(135deg, white, #E0F7F5) padding-box, linear-gradient(135deg, #00B4A6, #FF4D8D) border-box'
      : 'linear-gradient(135deg, white, #FFE5ED) padding-box, linear-gradient(135deg, #00B4A6, #FF4D8D) border-box',
    border: '2px solid transparent'
  } : {};

  // Адаптивные размеры в зависимости от типа блока
  const isDataBlock = block.category === 'data';
  const isAILayer = block.category === 'processing';
  const isCentral = block.category === 'central';

  const padding = isDataBlock ? 'p-5' : isCentral ? 'p-7' : 'p-6';
  const iconSize = isDataBlock ? 28 : isCentral ? 40 : 32;
  const titleSize = isDataBlock ? 'text-lg' : isCentral ? 'text-2xl' : 'text-lg';
  const subtitleSize = isDataBlock ? 'text-sm' : isCentral ? 'text-lg' : 'text-sm';

  return (
    <div
      className={`absolute ${sizeClasses[block.size]} ${categoryStyles[block.category]} rounded-lg ${padding} cursor-pointer transition-all duration-200 hover:scale-105 shadow-md group`}
      style={{
        left: `${block.position.x}%`,
        top: `${block.position.y}%`,
        transform: 'translate(-50%, -50%)',
        zIndex: 10,
        ...centralGradientStyle
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.boxShadow = '0 12px 24px rgba(0, 180, 166, 0.15), 0 4px 8px rgba(0, 0, 0, 0.1)';
        e.currentTarget.style.transform = 'translate(-50%, -52%) scale(1.05)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.boxShadow = '';
        e.currentTarget.style.transform = 'translate(-50%, -50%)';
      }}
      onClick={() => onClick(block)}
    >
      <div className={`flex flex-col h-full ${isAILayer ? 'text-white' : ''}`}>
        {/* Иконка */}
        <div className={`mb-2 ${isAILayer ? 'text-white' : 'text-primary'}`}>
          {Icon && <Icon size={iconSize} strokeWidth={2} />}
        </div>

        {/* Заголовок */}
        <h3 className={`${titleSize} font-bold mb-1 font-heading ${isAILayer ? 'text-white' : 'text-text-primary'}`}>
          {block.title}
        </h3>

        {/* Подзаголовок */}
        <p className={`${subtitleSize} leading-tight ${isAILayer ? 'text-white/90' : 'text-text-secondary'}`}>
          {block.subtitle}
        </p>
      </div>
    </div>
  );
}
