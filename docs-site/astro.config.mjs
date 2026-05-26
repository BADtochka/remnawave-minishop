import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import starlightThemeNova from 'starlight-theme-nova';

export default defineConfig({
  site: 'https://minishop.minidoc.cc',
  integrations: [
    starlight({
      title: 'Remnawave Minishop',
      description:
        'Документация по настройке, развертыванию и эксплуатации Remnawave Minishop.',
      plugins: [
        starlightThemeNova({
          nav: [
            { label: 'Запуск', href: '/reference/deployment/' },
            { label: 'Настройка', href: '/reference/configuration/' },
            { label: 'GitLab', href: 'https://gitlab.com/3252a8/remnawave-minshop' },
          ],
        }),
      ],
      favicon: '/favicon.svg',
      logo: {
        src: './src/assets/logo.svg',
        alt: 'Remnawave Minishop',
      },
      customCss: ['./src/styles/custom.css'],
      lastUpdated: false,
      locales: {
        root: {
          label: 'Русский',
          lang: 'ru',
        },
      },
      head: [
        {
          tag: 'meta',
          attrs: {
            name: 'theme-color',
            content: '#0f766e',
          },
        },
        {
          tag: 'meta',
          attrs: {
            property: 'og:site_name',
            content: 'Remnawave Minishop Docs',
          },
        },
      ],
      sidebar: [
        {
          label: 'Обзор',
          link: '/',
        },
        {
          label: 'Запуск',
          items: [
            { label: 'Настройка окружения', slug: 'reference/configuration' },
            { label: 'Переменные .env', slug: 'reference/env-vars' },
            { label: 'Развертывание', slug: 'reference/deployment' },
            { label: 'Миграция', slug: 'reference/migration-to-minishop' },
          ],
        },
        {
          label: 'Web App',
          items: [
            { label: 'Mini App', slug: 'reference/webapp' },
            { label: 'Темы и внешний вид', slug: 'reference/webapp-themes' },
            { label: 'Админ-панель', slug: 'reference/admin' },
            { label: 'Поддержка', slug: 'reference/support' },
          ],
        },
        {
          label: 'Продукт',
          items: [
            { label: 'Тарифы', slug: 'reference/tariffs' },
            { label: 'Архитектура', slug: 'reference/architecture' },
          ],
        },
      ],
    }),
  ],
});
