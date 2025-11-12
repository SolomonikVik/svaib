'use client';

import { blocks, connections, blockSizes } from '@/data/architectureData';

export default function ConnectionLines({ containerWidth = 800, containerHeight = 800 }) {
  // Вычисляем координаты точек подключения для каждого блока
  const getConnectionPoint = (blockId, direction = 'bottom') => {
    const block = blocks.find(b => b.id === blockId);
    if (!block) return { x: 0, y: 0 };

    const size = blockSizes[block.size];

    // Позиция центра блока в пикселях
    const centerX = (block.position.x / 100) * containerWidth;
    const centerY = (block.position.y / 100) * containerHeight;

    // Вычисляем точки подключения в зависимости от направления
    switch (direction) {
      case 'top':
        return { x: centerX, y: centerY - size.height / 2 };
      case 'bottom':
        return { x: centerX, y: centerY + size.height / 2 };
      case 'left':
        return { x: centerX - size.width / 2, y: centerY };
      case 'right':
        return { x: centerX + size.width / 2, y: centerY };
      default:
        return { x: centerX, y: centerY };
    }
  };

  // Генерируем path для каждой связи
  const generatePath = (from, to) => {
    const fromBlock = blocks.find(b => b.id === from);
    const toBlock = blocks.find(b => b.id === to);

    if (!fromBlock || !toBlock) return '';

    // Определяем направления подключения
    // От центральных блоков идёт вниз (bottom) к блокам данных (top)
    // От блоков данных идёт вниз (bottom) к AI-слою (top)
    const start = getConnectionPoint(from, 'bottom');
    const end = getConnectionPoint(to, 'top');

    // Создаём плавную кривую Безье
    const midY = (start.y + end.y) / 2;

    return `M ${start.x} ${start.y}
            C ${start.x} ${midY},
              ${end.x} ${midY},
              ${end.x} ${end.y}`;
  };

  return (
    <svg
      className="absolute inset-0 w-full h-full pointer-events-none"
      style={{ zIndex: 0 }}
    >
      <defs>
        {/* Градиент для линий */}
        <linearGradient id="lineGradient" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#00B4A6" stopOpacity="0.3" />
          <stop offset="100%" stopColor="#FF4D8D" stopOpacity="0.3" />
        </linearGradient>

        {/* Animated gradient для эффекта потока */}
        <linearGradient id="flowGradient" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#00B4A6" stopOpacity="0.6">
            <animate
              attributeName="offset"
              values="0;1;0"
              dur="3s"
              repeatCount="indefinite"
            />
          </stop>
          <stop offset="50%" stopColor="#FF4D8D" stopOpacity="0.6">
            <animate
              attributeName="offset"
              values="0.5;1;0.5"
              dur="3s"
              repeatCount="indefinite"
            />
          </stop>
          <stop offset="100%" stopColor="#00B4A6" stopOpacity="0.6">
            <animate
              attributeName="offset"
              values="1;0;1"
              dur="3s"
              repeatCount="indefinite"
            />
          </stop>
        </linearGradient>
      </defs>

      {/* Отрисовываем все связи */}
      {connections.map((connection, index) => {
        const path = generatePath(connection.from, connection.to);
        return (
          <g key={`${connection.from}-${connection.to}-${index}`}>
            {/* Основная линия (статичная) */}
            <path
              d={path}
              stroke="url(#lineGradient)"
              strokeWidth="2"
              fill="none"
              strokeLinecap="round"
            />

            {/* Анимированная линия поверх */}
            <path
              d={path}
              stroke="url(#flowGradient)"
              strokeWidth="2"
              fill="none"
              strokeLinecap="round"
              strokeDasharray="10 10"
              className="animate-flow"
            />
          </g>
        );
      })}
    </svg>
  );
}
