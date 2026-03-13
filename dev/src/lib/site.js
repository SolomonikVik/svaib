export const siteConfig = {
  name: 'svaib',
  url: 'https://svaib.com',
  title: 'svaib — Second AI Brain для руководителя',
  description: 'Управленческий дизайн, упакованный в AI. Данные у вас, методология у нас.',
  telegramUrl: 'https://t.me/solomonikvik',
  telegramChannelUrl: 'https://t.me/svaib_lab',
  githubUrl: 'https://github.com/SolomonikVik/svaib',
};

export function isInternalVoteEnabled() {
  return process.env.ENABLE_INTERNAL_VOTE === 'true';
}

export function buildMetadata({
  title,
  description,
  path = '/',
}) {
  const metadataTitle = title ? `${title} | ${siteConfig.name}` : siteConfig.title;
  const metadataDescription = description || siteConfig.description;
  const url = `${siteConfig.url}${path === '/' ? '' : path}`;

  return {
    title: metadataTitle,
    description: metadataDescription,
    alternates: {
      canonical: path,
    },
    openGraph: {
      title: metadataTitle,
      description: metadataDescription,
      url,
      siteName: siteConfig.name,
      locale: 'ru_RU',
      type: 'website',
    },
    twitter: {
      card: 'summary_large_image',
      title: metadataTitle,
      description: metadataDescription,
    },
  };
}

