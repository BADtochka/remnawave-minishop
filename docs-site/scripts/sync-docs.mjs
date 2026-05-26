import { copyFile, mkdir, readdir, readFile, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const siteRoot = path.resolve(fileURLToPath(new URL('..', import.meta.url)));
const repoRoot = path.resolve(siteRoot, '..');
const sourceDir = path.join(repoRoot, 'docs');
const outputDir = path.join(siteRoot, 'src', 'content', 'docs');

const descriptions = {
  'index.md': 'Документация по запуску, настройке и сопровождению Telegram Mini App для Remnawave.',
  'getting-started/overview.md': 'Что входит в Remnawave Minishop и как связаны бот, Mini App, backend, worker и Remnawave Panel.',
  'getting-started/setup.md': 'Минимальный путь запуска Remnawave Minishop через Docker Compose.',
  'configuration/security.md': 'Секреты, публичные URL, доступ администраторов и базовые меры защиты Minishop.',
  'configuration/env-vars.md': 'Полный справочник переменных окружения Remnawave Minishop.',
  'features/core.md': 'Пользовательские и админские сценарии Remnawave Minishop.',
  'features/payments.md': 'Платежные провайдеры, кнопки оплаты и webhook-обработка.',
  'features/subscriptions.md': 'Period- и traffic-тарифы, premium-сквады, HWID-устройства и жизненный цикл подписки.',
  'features/tariffs.md': 'Каталог тарифов, period/traffic-модели, premium-сквады и HWID-устройства.',
  'features/web-app.md': 'Telegram Mini App, авторизация, публичные инструкции и проксирование.',
  'features/webapp-themes.md': 'Кастомные темы, CSS-токены, ассеты и пайплайн создания темы.',
  'features/admin-panel.md': 'Возможности админ-панели, управление пользователями, настройками, тарифами и поддержкой.',
  'features/support.md': 'Пользовательские тикеты, админский inbox, уведомления и лимиты поддержки.',
  'deploy-examples/index.md': 'Как выбрать готовый deploy example для production или проверки.',
  'deploy-examples/caddy.md': 'Запуск Remnawave Minishop с Caddy и автоматическим HTTPS.',
  'deploy-examples/nginx.md': 'Запуск Remnawave Minishop с Nginx и внешними TLS-сертификатами.',
  'deploy-examples/newt.md': 'Запуск через Pangolin/Newt без входящих портов на сервере приложения.',
  'deploy-examples/no-proxy.md': 'Прямой запуск backend и frontend портов без reverse proxy.',
  'migrations/index.md': 'Готовые сценарии миграции в Remnawave Minishop с других ботов.',
  'migrations/remnawave-tg-shop.md': 'Перенос данных со старого remnawave-tg-shop на split-архитектуру Minishop.',
  'payments/yookassa.md': 'Быстрый вход в настройку YooKassa для Remnawave Minishop.',
  'payments/freekassa.md': 'Быстрый вход в настройку FreeKassa для Remnawave Minishop.',
  'payments/platega.md': 'Настройка Platega, отдельных СБП/карта и crypto-кнопок.',
  'payments/severpay.md': 'Настройка SeverPay, MID, token, return URL и срока жизни ссылки.',
  'payments/wata.md': 'Настройка Wata, API token, TTL ссылки, подписи webhook и trusted IP.',
  'payments/cryptopay.md': 'Настройка CryptoPay, токена, сети, currency type и asset.',
  'payments/heleket.md': 'Настройка Heleket, merchant ID, payment API key, invoice currency и webhook-проверок.',
  'payments/telegram-stars.md': 'Оплата подписок и докупок через Telegram Stars.',
  'administration/users.md': 'Где управлять пользователями, подписками, блокировками и поддержкой.',
  'administration/maintenance.md': 'Обновления, миграции, резервные копии и проверки production-стека.',
  'troubleshooting/issues.md': 'Короткие чеклисты для частых проблем запуска, вебхуков, Mini App и платежей.',
  'troubleshooting/logs.md': 'Какие логи смотреть при диагностике backend, worker, frontend, миграций и вебхуков.',
  'architecture.md': 'Краткая архитектура backend, frontend, worker и инфраструктурных сервисов.',
  'configuration.md': 'Минимальный .env, bootstrap-секреты и настройка через Web App админку.',
  'deployment.md': 'Docker Compose, reverse proxy, TLS, образы, обновления и резервные копии.',
};

const imageExtensions = new Set(['.avif', '.gif', '.jpeg', '.jpg', '.png', '.svg', '.webp']);

function yamlString(value) {
  return JSON.stringify(value);
}

function toPosix(relativePath) {
  return relativePath.split(path.sep).join('/');
}

function outputRelativePath(sourceRelativePath) {
  if (sourceRelativePath === 'index.md') {
    return 'index.md';
  }
  if (!sourceRelativePath.includes('/')) {
    return `reference/${sourceRelativePath}`;
  }
  return sourceRelativePath;
}

function pagePathForSource(sourceRelativePath, hash = '') {
  const output = outputRelativePath(sourceRelativePath).replace(/\.md$/i, '');
  const route = output === 'index' ? '/' : `/${output.replace(/\/index$/u, '')}/`;
  return `${route}${hash}`;
}

function titleForRelativePath(relativePath) {
  const baseName = path.posix.basename(relativePath, '.md');
  return baseName;
}

function extractTitle(relativePath, content) {
  const match = content.match(/^#\s+(.+?)\s*$/m);
  return match?.[1] ?? titleForRelativePath(relativePath);
}

function stripFirstHeading(content) {
  return content.replace(/^#\s+.+?\s*\r?\n+/, '');
}

function rewriteMarkdownLinks(markdown, sourceRelativePath) {
  const sourceDirectory = path.posix.dirname(sourceRelativePath);
  return markdown.replace(/\]\((?!https?:\/\/|mailto:|tel:|\/|#)([^)\s]+\.md)(#[^)]+)?\)/g, (match, target, hash = '') => {
    const resolvedTarget = path.posix.normalize(path.posix.join(sourceDirectory, target));
    return `](${pagePathForSource(resolvedTarget, hash)})`;
  });
}

function normalizeCodeFences(markdown) {
  return markdown
    .replace(/^```env\s*$/gim, '```ini')
    .replace(/^```caddyfile\s*$/gim, '```txt');
}

function extraFrontmatter(sourceRelativePath) {
  if (sourceRelativePath !== 'index.md') {
    return [];
  }

  return [
    'template: splash',
    'hero:',
    '  tagline: "Telegram-бот и Mini App для продажи подписок Remnawave: платежи, тарифы, админка, поддержка и инструкции подключения."',
    '  image:',
    '    html: \'<img class="minishop-hero-screenshot" src="/remnawave-minishop.webp" alt="Интерфейс Remnawave Minishop" width="1920" height="1080" loading="eager" decoding="async" />\'',
    '  actions:',
    '    - text: "Быстрый старт"',
    '      link: /getting-started/setup/',
    '      icon: right-arrow',
    '    - text: "Deploy examples"',
    '      link: /deploy-examples/',
    '      icon: setting',
    '      variant: minimal',
  ];
}

function frontmatter({ title, description, sourceRelativePath }) {
  const editPath = sourceRelativePath
    .split('/')
    .map((segment) => encodeURIComponent(segment))
    .join('/');
  const editUrl = `https://gitlab.com/3252a8/remnawave-minshop/-/edit/main/docs/${editPath}`;
  return [
    '---',
    `title: ${yamlString(title)}`,
    `description: ${yamlString(description)}`,
    `editUrl: ${yamlString(editUrl)}`,
    ...extraFrontmatter(sourceRelativePath),
    '---',
    '',
  ].join('\n');
}

async function walk(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const absolutePath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      files.push(...(await walk(absolutePath)));
      continue;
    }
    if (entry.isFile()) {
      files.push(absolutePath);
    }
  }
  return files;
}

async function syncMarkdown(files) {
  for (const sourcePath of files.filter((file) => file.endsWith('.md'))) {
    const sourceRelativePath = toPosix(path.relative(sourceDir, sourcePath));
    const outputRelative = outputRelativePath(sourceRelativePath);
    const outputPath = path.join(outputDir, ...outputRelative.split('/'));
    const content = await readFile(sourcePath, 'utf8');
    const title = extractTitle(sourceRelativePath, content);
    const body = normalizeCodeFences(
      rewriteMarkdownLinks(stripFirstHeading(content).trimStart(), sourceRelativePath),
    );
    const output = frontmatter({
      title,
      description: descriptions[sourceRelativePath] ?? title,
      sourceRelativePath,
    });

    await mkdir(path.dirname(outputPath), { recursive: true });
    await writeFile(outputPath, `${output}${body}\n`, 'utf8');
  }
}

async function syncAssets(files) {
  for (const sourcePath of files.filter((file) => imageExtensions.has(path.extname(file).toLowerCase()))) {
    const sourceRelativePath = toPosix(path.relative(sourceDir, sourcePath));
    const outputRelative = !sourceRelativePath.includes('/')
      ? sourceRelativePath
      : sourceRelativePath;
    const outputPath = path.join(outputDir, ...outputRelative.split('/'));
    await mkdir(path.dirname(outputPath), { recursive: true });
    await copyFile(sourcePath, outputPath);

    if (!sourceRelativePath.includes('/')) {
      const referenceOutputPath = path.join(outputDir, 'reference', sourceRelativePath);
      await mkdir(path.dirname(referenceOutputPath), { recursive: true });
      await copyFile(sourcePath, referenceOutputPath);
    }
  }
}

await rm(outputDir, { recursive: true, force: true });
await mkdir(outputDir, { recursive: true });

const files = await walk(sourceDir);
await syncMarkdown(files);
await syncAssets(files);

console.log(`Synced documentation from ${path.relative(repoRoot, sourceDir)} to ${path.relative(repoRoot, outputDir)}`);
