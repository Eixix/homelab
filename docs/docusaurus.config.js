// @ts-check
import {themes as prismThemes} from 'prism-react-renderer';

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'Homelab Docs',
  tagline: 'Runbooks, migration notes, and operating decisions',
  url: 'https://docs.home',
  baseUrl: '/',
  organizationName: 'Eixix',
  projectName: 'homelab',
  onBrokenLinks: 'warn',
  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },
  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          path: '.',
          routeBasePath: 'docs',
          sidebarPath: './sidebars.js',
          exclude: [
            'node_modules/**',
            'src/**',
            'static/**',
            'build/**',
            'inventory/**',
          ],
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      }),
    ],
  ],
  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      colorMode: {
        defaultMode: 'dark',
        respectPrefersColorScheme: true,
      },
      navbar: {
        title: 'Homelab Docs',
        items: [
          {
            type: 'docSidebar',
            sidebarId: 'homelabSidebar',
            position: 'left',
            label: 'Docs',
          },
          {
            href: 'https://github.com/Eixix/homelab',
            label: 'GitHub',
            position: 'right',
          },
        ],
      },
      footer: {
        style: 'dark',
        copyright: 'Homelab documentation. Built with Docusaurus.',
      },
      prism: {
        theme: prismThemes.github,
        darkTheme: prismThemes.dracula,
      },
    }),
};

export default config;
