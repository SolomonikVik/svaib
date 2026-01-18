export const metadata = {
  title: 'Голосование | svaib',
  description: 'Система голосования для стратсессий',
};

export default function VoteLayout({ children }) {
  return (
    <div className="min-h-screen bg-[#F0FDFB]">
      <header className="bg-white border-b border-[#E0F7F5] px-4 py-3">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="font-heading font-bold text-xl">
            <span className="text-[#00B4A6]">sv</span>
            <span className="text-[#FF4D8D]">ai</span>
            <span className="text-[#00B4A6]">b</span>
            <span className="text-gray-400 font-normal text-sm ml-2">vote</span>
          </div>
          <nav className="flex gap-4 text-sm">
            <a href="/vote" className="text-gray-600 hover:text-[#00B4A6]">Голосование</a>
            <a href="/vote/results" className="text-gray-600 hover:text-[#00B4A6]">Результаты</a>
          </nav>
        </div>
      </header>
      <main className="max-w-4xl mx-auto px-4 py-8">
        {children}
      </main>
    </div>
  );
}
