module.exports = {
  packagerConfig: {
    name: 'JARVIS AI',
    executableName: 'jarvis',
    asar: true,
    icon: '../frontend/public/favicon',
    ignore: [
      /^\/src\//,
      /^\/\.git\//,
      /node_modules\/.*\/src\//,
    ],
  },
  makers: [
    {
      name: '@electron-forge/maker-squirrel',
      config: {
        name: 'JARVIS_AI',
        setupIcon: '../frontend/public/favicon.ico',
      },
    },
    {
      name: '@electron-forge/maker-zip',
      platforms: ['darwin'],
    },
    {
      name: '@electron-forge/maker-deb',
      config: {
        options: {
          maintainer: 'JARVIS Team',
          homepage: 'https://jarvis.ai',
        },
      },
    },
  ],
  hooks: {
    packageAfterCopy: async (forgeConfig, buildPath, electronVersion, platform, arch) => {
      console.log(`Packaged for ${platform} (${arch}) with Electron ${electronVersion}`);
    },
  },
};
