'use client';

import * as Dialog from '@radix-ui/react-dialog';
import * as Icons from 'lucide-react';
import { X } from 'lucide-react';

export default function BlockModal({ block, isOpen, onClose }) {
  if (!block) return null;

  const Icon = Icons[block.icon];

  return (
    <Dialog.Root open={isOpen} onOpenChange={onClose}>
      <Dialog.Portal>
        {/* Overlay (затемнённый фон) */}
        <Dialog.Overlay className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 animate-in fade-in" />

        {/* Modal Content */}
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-2xl max-h-[85vh] overflow-y-auto bg-white rounded-xl shadow-xl z-50 animate-in fade-in zoom-in-95">
          {/* Header */}
          <div className="sticky top-0 bg-white border-b border-border px-8 py-6 flex items-start justify-between">
            <div className="flex items-start gap-4">
              {/* Иконка */}
              <div className="w-12 h-12 rounded-lg bg-primary-light flex items-center justify-center flex-shrink-0">
                {Icon && <Icon size={24} className="text-primary" strokeWidth={2} />}
              </div>

              {/* Заголовок */}
              <div>
                <Dialog.Title className="text-2xl font-bold text-text-primary font-heading">
                  {block.title}
                </Dialog.Title>
                <Dialog.Description className="text-base text-text-secondary mt-1">
                  {block.subtitle}
                </Dialog.Description>
              </div>
            </div>

            {/* Close button */}
            <Dialog.Close asChild>
              <button
                className="w-8 h-8 rounded-lg hover:bg-background transition-colors flex items-center justify-center flex-shrink-0"
                aria-label="Закрыть"
              >
                <X size={20} className="text-text-secondary" />
              </button>
            </Dialog.Close>
          </div>

          {/* Body */}
          <div className="px-8 py-6 space-y-6">
            {/* Description */}
            {block.description && (
              <div>
                <h3 className="text-lg font-semibold text-text-primary mb-2 font-heading">
                  О модуле
                </h3>
                <p className="text-base text-text-secondary leading-relaxed">
                  {block.description}
                </p>
              </div>
            )}

            {/* Features */}
            {block.features && block.features.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold text-text-primary mb-3 font-heading">
                  Возможности
                </h3>
                <ul className="space-y-2">
                  {block.features.map((feature, index) => (
                    <li key={index} className="flex items-start gap-3">
                      <div className="w-5 h-5 rounded-full bg-primary-light flex items-center justify-center flex-shrink-0 mt-0.5">
                        <div className="w-2 h-2 rounded-full bg-primary"></div>
                      </div>
                      <span className="text-base text-text-secondary leading-relaxed">
                        {feature}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* How it works */}
            {block.howItWorks && (
              <div>
                <h3 className="text-lg font-semibold text-text-primary mb-2 font-heading">
                  Как это работает
                </h3>
                <p className="text-base text-text-secondary leading-relaxed">
                  {block.howItWorks}
                </p>
              </div>
            )}

            {/* Benefits */}
            {block.benefits && (
              <div>
                <h3 className="text-lg font-semibold text-text-primary mb-2 font-heading">
                  Ценность
                </h3>
                <p className="text-base text-text-secondary leading-relaxed">
                  {block.benefits}
                </p>
              </div>
            )}

            {/* Technical Details (если есть) */}
            {block.technicalDetails && (
              <div className="bg-background rounded-lg p-4">
                <h3 className="text-sm font-semibold text-text-primary mb-2 font-heading">
                  Технические детали
                </h3>
                <p className="text-sm text-text-secondary leading-relaxed">
                  {block.technicalDetails}
                </p>
              </div>
            )}
          </div>

          {/* Footer */}
          {block.exampleLink && (
            <div className="sticky bottom-0 bg-white border-t border-border px-8 py-6">
              <a
                href={block.exampleLink}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 gradient-cta text-white px-6 py-3 rounded-lg font-semibold text-base transition-all hover:shadow-lg hover:scale-105"
              >
                <Icons.ExternalLink size={18} />
                Посмотреть пример
              </a>
            </div>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
