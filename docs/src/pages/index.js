import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';
import styles from './index.module.css';

const links = [
  {
    title: 'Migration TODO',
    href: '/docs/prod-migration-todo',
    description: 'Current production migration status, remaining decisions, and cleanup work.',
  },
  {
    title: 'Backups',
    href: '/docs/backup',
    description: 'Encrypted homelab backups, scheduling, storage-array sync, and restore outline.',
  },
  {
    title: 'Post-Migration Ops',
    href: '/docs/post-migration-ops',
    description: 'Restore drill, credential rotation, Step CA choice, and independent project follow-ups.',
  },
  {
    title: 'Storage Array',
    href: '/docs/storage-array-zfs',
    description: 'ZFS pool review, hardening options, scrub cadence, and alerting notes.',
  },
  {
    title: 'Network Isolation',
    href: '/docs/network-isolation',
    description: 'Current Docker network boundaries and the target per-stack hardening model.',
  },
  {
    title: 'Onboarding',
    href: '/docs/presentations/homelab-onboarding',
    description: 'Deutschsprachige Marp-Schulung fuer neue Homelab-Nutzer mit leichtem Corporate-Augenzwinkern.',
  },
  {
    title: 'Remaining Projects',
    href: '/docs/remaining-projects',
    description: 'Live services still outside this repo, their routes, data paths, and next decisions.',
  },
  {
    title: 'Cutover Runbooks',
    href: '/docs/app-cutover-runbook',
    description: 'Service-by-service production migration notes and rollback commands.',
  },
];

export default function Home() {
  return (
    <Layout title="Homelab Docs" description="Homelab runbooks and architecture decisions">
      <main className={styles.main}>
        <section className={styles.hero}>
          <p className={styles.eyebrow}>Homelab</p>
          <h1>Operations notes without the archeology.</h1>
          <p className={styles.lede}>
            Runbooks, migration state, backup paths, and infrastructure decisions collected in one internal place.
          </p>
        </section>
        <section className={styles.grid}>
          {links.map((link) => (
            <Link className={styles.card} to={link.href} key={link.href}>
              <span>{link.title}</span>
              <p>{link.description}</p>
            </Link>
          ))}
        </section>
      </main>
    </Layout>
  );
}
