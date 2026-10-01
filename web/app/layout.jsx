import './globals.css';

export const metadata = {
  title: 'PaperTrail - audit-ready risk & regulatory copilot',
  description:
    'Every figure resolves to its governed metric, the exact SQL, the source rows and the clause that makes it matter. Built on Snowflake for the CoCo CLI Hackathon.',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans+Condensed:wght@400;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Serif:wght@400;500&display=swap"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
