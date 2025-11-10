const Terms = () => {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Hero Section */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <div className="text-center">
            <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-6">
              Terms of Service
            </h1>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Please read these terms carefully before using our website and services.
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
              <h2 className="text-2xl font-bold text-gray-900 mb-4">1. Acceptance of Terms</h2>
              <p className="text-gray-700 mb-4">
                By accessing and using this website, you accept and agree to be bound by the terms 
                and provision of this agreement. If you do not agree to abide by the above, please 
                do not use this service.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">2. Purpose and Scope</h2>
              <p className="text-gray-700 mb-4">
                This website serves as a documentation platform for police interactions during 
                public demonstrations. All information presented is derived from publicly available 
                sources and is intended for educational and transparency purposes.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">3. Information Accuracy</h2>
              <p className="text-gray-700 mb-4">
                While we strive to ensure the accuracy of all information presented, we make no 
                warranties or representations about the completeness, accuracy, or reliability of 
                the content. All information is provided "as is" without warranty of any kind.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">4. Source Attribution</h2>
              <p className="text-gray-700 mb-4">
                All content is sourced from publicly available materials including news reports, 
                social media posts, official statements, and other public records. We provide 
                links to original sources whenever possible to allow independent verification.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">5. User Conduct</h2>
              <p className="text-gray-700 mb-4">
                Users agree to use this website in a lawful manner and not to:
              </p>
              <ul className="list-disc list-inside text-gray-700 mb-4 space-y-2">
                <li>Engage in any form of harassment or intimidation</li>
                <li>Use the information for illegal purposes</li>
                <li>Attempt to identify private individuals not already in the public record</li>
                <li>Distribute false or misleading information</li>
              </ul>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">6. Privacy and Data Protection</h2>
              <p className="text-gray-700 mb-4">
                We are committed to protecting user privacy. Please refer to our Privacy Policy 
                for detailed information about how we collect, use, and protect your information.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">7. Intellectual Property</h2>
              <p className="text-gray-700 mb-4">
                The design and layout of this website are protected by copyright. However, the 
                factual information presented is derived from public sources and is intended for 
                public knowledge and transparency.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">8. Limitation of Liability</h2>
              <p className="text-gray-700 mb-4">
                In no event shall the Accountability Campaign be liable for any direct, indirect, 
                incidental, special, or consequential damages arising out of or in connection with 
                your use of this website.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">9. Corrections and Updates</h2>
              <p className="text-gray-700 mb-4">
                We are committed to accuracy and will promptly correct any factual errors brought 
                to our attention. If you believe any information is inaccurate, please contact us 
                with supporting documentation.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">10. Changes to Terms</h2>
              <p className="text-gray-700 mb-4">
                We reserve the right to modify these terms at any time. Changes will be effective 
                immediately upon posting to this website. Your continued use of the website 
                constitutes acceptance of any changes.
              </p>
            </section>

            <section className="mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">11. Governing Law</h2>
              <p className="text-gray-700 mb-4">
                These terms shall be governed by and construed in accordance with applicable local 
                and federal laws, including First Amendment protections for free speech and press.
              </p>
            </section>

            <section>
              <h2 className="text-2xl font-bold text-gray-900 mb-4">12. Contact Information</h2>
              <p className="text-gray-700">
                If you have any questions about these Terms of Service, please contact us through 
                the appropriate channels provided on this website.
              </p>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Terms;

