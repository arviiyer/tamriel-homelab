module.exports = {
  platform: 'forgejo',
  endpoint: 'https://git.example.com',
  gitAuthor: 'Renovate Bot <renovate@example.com>',
  repositories: ['homelab/apps'],
  autodiscover: false,

  // Keep the policy here; repositories may add their own renovate.json later.
  onboarding: false,
  requireConfig: 'optional',
  enabledManagers: ['docker-compose', 'dockerfile'],
  baseBranchPatterns: ['main'],
  dependencyDashboard: false,
  automerge: false,
  prHourlyLimit: 2,
  prConcurrentLimit: 5,

  packageRules: [
    {
      matchDatasources: ['docker'],
      pinDigests: true,
    },
    {
      matchUpdateTypes: ['patch'],
      groupName: 'patch updates',
    },
  ],
};
