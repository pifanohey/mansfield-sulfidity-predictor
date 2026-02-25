/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable standalone output for Docker deployment
  output: "standalone",

  async rewrites() {
    // Use environment variable for API URL, fallback to localhost for development
    const apiUrl = process.env.API_URL || "http://127.0.0.1:8005";
    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
