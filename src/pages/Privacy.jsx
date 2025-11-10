const Privacy = () => {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Hero Section */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <div className="text-center">
            <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-6">
              Privacy Policy
            </h1>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Your privacy is important to us. This policy explains how we handle your information.
            </p>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="bg-white rounded-lg p-8 shadow-md">
          <div className="prose prose-lg max-w-none">
            <p className="text-sm text-gray-600 mb-8">
              Last updated: {new Date().toLocaleDateString()}
            </p>

            <section className="mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">1. Information We Collect</h2>
              <p className="text-gray-700 mb-4">
                This website is designed to minimize data collection. We may collect:
              </p>
              <ul className="list-disc list-inside text-gray-700 mb-4 space-y-2">
                <li>Basic website analytics (page views, general location, device type)</li>
                <li>Technical information necessary for website functionality</li>
                <li>Information you voluntarily provide when contacting us</li>
              </ul>
              <p className="text-gray-700 mb-4">
                We do not collect personal identifying information unless voluntarily provided.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">2. How We Use Information</h2>
              <p className="text-gray-700 mb-4">
                Any information collected is used solely for:
              </p>
              <ul className="list-disc list-inside text-gray-700 mb-4 space-y-2">
                <li>Improving website functionality and user experience</li>
                <li>Understanding general usage patterns</li>
                <li>Responding to inquiries or feedback</li>
                <li>Ensuring website security and preventing abuse</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">3. Information Sharing</h2>
              <p className="text-gray-700 mb-4">
                We do not sell, trade, or otherwise transfer your personal information to third 
                parties. We may share information only in the following circumstances:
              </p>
              <ul className="list-disc list-inside text-gray-700 mb-4 space-y-2">
                <li>When required by law or legal process</li>
                <li>To protect our rights, property, or safety</li>
                <li>With your explicit consent</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">4. Public Information</h2>
              <p className="text-gray-700 mb-4">
                All officer information displayed on this website is derived from publicly 
                available sources including:
              </p>
              <ul className="list-disc list-inside text-gray-700 mb-4 space-y-2">
                <li>News reports and media coverage</li>
                <li>Social media posts and public statements</li>
                <li>Official government records and reports</li>
                <li>Court documents and legal filings</li>
              </ul>
              <p className="text-gray-700 mb-4">
                We do not collect or display private information not already in the public domain.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">5. Cookies and Tracking</h2>
              <p className="text-gray-700 mb-4">
                This website may use minimal cookies for:
              </p>
              <ul className="list-disc list-inside text-gray-700 mb-4 space-y-2">
                <li>Basic website functionality</li>
                <li>Remembering user preferences</li>
                <li>Anonymous analytics to improve the site</li>
              </ul>
              <p className="text-gray-700 mb-4">
                You can disable cookies in your browser settings, though this may affect 
                website functionality.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">6. Data Security</h2>
              <p className="text-gray-700 mb-4">
                We implement appropriate security measures to protect against unauthorized access, 
                alteration, disclosure, or destruction of information. However, no method of 
                transmission over the internet is 100% secure.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">7. Third-Party Links</h2>
              <p className="text-gray-700 mb-4">
                This website contains links to external sources and third-party websites. We are 
                not responsible for the privacy practices or content of these external sites. 
                We encourage you to review the privacy policies of any third-party sites you visit.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">8. Children's Privacy</h2>
              <p className="text-gray-700 mb-4">
                This website is not intended for children under 13 years of age. We do not 
                knowingly collect personal information from children under 13.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">9. Your Rights</h2>
              <p className="text-gray-700 mb-4">
                You have the right to:
              </p>
              <ul className="list-disc list-inside text-gray-700 mb-4 space-y-2">
                <li>Request information about data we may have collected</li>
                <li>Request correction of any inaccurate information</li>
                <li>Request deletion of your personal information</li>
                <li>Opt out of any communications</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">10. Changes to This Policy</h2>
              <p className="text-gray-700 mb-4">
                We may update this privacy policy from time to time. Changes will be posted on 
                this page with an updated revision date. Your continued use of the website after 
                any changes constitutes acceptance of the new policy.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-gray-900 mb-4">11. Contact Us</h2>
              <p className="text-gray-700">
                If you have any questions about this Privacy Policy or our data practices, 
                please contact us through the appropriate channels provided on this website.
              </p>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Privacy;

