export default function Footer() {
  return (
    <footer className="bg-background-secondary py-12 px-6 border-t border-border">
      <div className="max-w-6xl mx-auto">
        <div className="grid md:grid-cols-4 gap-8 mb-8">
          {/* Колонка 1 - О проекте */}
          <div>
            <h3 className="text-lg font-semibold mb-4 font-heading">svaib</h3>
            <p className="text-text-secondary text-sm leading-relaxed">
              AI-мастерская, создающая управленческие решения для структурированных встреч
            </p>
          </div>

          {/* Колонка 2 - Контакты */}
          <div>
            <h4 className="text-sm font-semibold mb-4 font-heading">Контакты</h4>
            <ul className="space-y-2">
              <li>
                <a
                  href="https://t.me/NikMer"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-text-secondary hover:text-primary transition-colors"
                >
                  Telegram: @NikMer
                </a>
              </li>
              <li>
                <a
                  href="https://t.me/osvaivaemsa"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-text-secondary hover:text-primary transition-colors"
                >
                  Канал: освAIваемся
                </a>
              </li>
            </ul>
          </div>

          {/* Колонка 3 - Ресурсы */}
          <div>
            <h4 className="text-sm font-semibold mb-4 font-heading">Ресурсы</h4>
            <ul className="space-y-2">
              <li>
                <a
                  href="https://github.com/SolomonikVik/svaib"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-text-secondary hover:text-primary transition-colors"
                >
                  GitHub (Open Source)
                </a>
              </li>
              <li>
                <a
                  href="https://drive.google.com/drive/folders/1oqL07qpjkkQomXeOajJ6RfUsnITgAgxC"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-text-secondary hover:text-primary transition-colors"
                >
                  Примеры системы
                </a>
              </li>
            </ul>
          </div>

          {/* Колонка 4 - Архив */}
          <div>
            <h4 className="text-sm font-semibold mb-4 font-heading">Архив</h4>
            <ul className="space-y-2">
              <li>
                <a
                  href="/archive/index.html"
                  className="text-sm text-text-secondary hover:text-primary transition-colors"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Старая версия
                </a>
              </li>
              <li>
                <a
                  href="/archive/mvp-present.html"
                  className="text-sm text-text-secondary hover:text-primary transition-colors"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  MVP презентация
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="pt-8 border-t border-border text-center">
          <p className="text-sm text-text-secondary">
            © 2025 svaib. Open Source проект.
          </p>
        </div>
      </div>
    </footer>
  );
}
