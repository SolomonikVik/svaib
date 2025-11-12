'use client';

import { useState, useRef, useEffect } from 'react';
import { blocks } from '@/data/architectureData';
import ArchBlock from './ArchBlock';
import ConnectionLines from './ConnectionLines';
import BlockModal from './BlockModal';

export default function Architecture() {
  const [activeBlock, setActiveBlock] = useState(null);
  const [containerSize, setContainerSize] = useState({ width: 800, height: 800 });
  const containerRef = useRef(null);

  useEffect(() => {
    const updateSize = () => {
      if (containerRef.current) {
        const { width, height } = containerRef.current.getBoundingClientRect();
        setContainerSize({ width, height });
      }
    };

    // Установить размеры сразу
    updateSize();

    // Обновлять при resize
    window.addEventListener('resize', updateSize);
    return () => window.removeEventListener('resize', updateSize);
  }, []);

  const handleBlockClick = (block) => {
    setActiveBlock(block);
  };

  return (
    <section className="py-24 px-6 bg-white">
      <div className="max-w-7xl mx-auto">
        <h2 className="text-4xl font-bold text-center mb-4 font-heading">
          Как работает AI-менеджмент
        </h2>
        <p className="text-xl text-text-secondary text-center mb-8 max-w-3xl mx-auto">
          Управляем целями, метриками, задачами, встречами<br />
          и держим все в AI-памяти.
        </p>

        {/* Подсказка */}
        <div className="flex items-center justify-center gap-2 mb-6 text-sm text-text-secondary">
          <svg className="w-5 h-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
          </svg>
          <span>Нажмите на блок, чтобы узнать подробности</span>
        </div>

        {/* Канвас с блоками */}
        <div
          ref={containerRef}
          className="relative w-full h-[800px] bg-background rounded-xl border border-border overflow-hidden"
        >
          {/* SVG связи (позади блоков) */}
          <ConnectionLines containerWidth={containerSize.width} containerHeight={containerSize.height} />

          {/* Блоки (поверх связей) */}
          {blocks.map((block) => (
            <ArchBlock
              key={block.id}
              block={block}
              onClick={handleBlockClick}
            />
          ))}
        </div>

        {/* Легенда */}
        <div className="flex flex-wrap justify-center gap-8 mt-8 text-sm text-text-secondary">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded border-2 border-accent"></div>
            <span>Интерфейс</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded border-2 border-primary bg-white"></div>
            <span>Блоки данных</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded gradient-cta"></div>
            <span>AI-обработка</span>
          </div>
        </div>

        {/* Модальное окно */}
        <BlockModal
          block={activeBlock}
          isOpen={!!activeBlock}
          onClose={() => setActiveBlock(null)}
        />
      </div>
    </section>
  );
}
