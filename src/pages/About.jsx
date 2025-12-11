import { Mail, Globe, Users, Heart } from 'lucide-react';
import { Card } from '@/components/ui/card';

const About = () => {
  return (
    <div className="min-h-screen bg-slate-50">
      {/* Hero Section */}
      <div className="bg-white border-b border-slate-200">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <div className="text-center">
            <h1 className="text-4xl md:text-5xl font-bold text-slate-900 mb-6">
              About Us
            </h1>
            <p className="text-xl text-slate-600 max-w-3xl mx-auto">
              An independent research initiative dedicated to promoting transparency,
              accountability, and the protection of civil liberties.
            </p>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        {/* Mission Statement */}
        <div className="bg-white rounded-lg p-8 border border-slate-200 mb-12">
          <h2 className="text-2xl font-bold text-slate-900 mb-6">Our Mission</h2>
          <p className="text-lg text-slate-700 leading-relaxed mb-6">
            The Palestine Accountability Campaign is an independent research initiative focused
            on documenting police conduct during public demonstrations in the UK. We believe
            that transparency and factual documentation serve the public interest.
          </p>
          <p className="text-lg text-slate-700 leading-relaxed">
            Our work is grounded in respect for civil liberties, democratic principles,
            and the belief that accountability strengthens public trust in policing.
          </p>
        </div>

        {/* Values */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-12">
          <Card className="p-6 border border-slate-200">
            <Users className="h-8 w-8 text-slate-600 mb-4" />
            <h3 className="text-xl font-semibold text-slate-900 mb-3">Independent Research</h3>
            <p className="text-slate-700">
              We operate as an independent research project, maintaining objectivity
              and evidence-based documentation.
            </p>
          </Card>

          <Card className="p-6 border border-slate-200">
            <Globe className="h-8 w-8 text-slate-600 mb-4" />
            <h3 className="text-xl font-semibold text-slate-900 mb-3">Evidence-Based</h3>
            <p className="text-slate-700">
              All documentation relies on publicly available sources and verifiable
              information, ensuring accuracy and credibility.
            </p>
          </Card>

          <Card className="p-6 border border-slate-200">
            <Heart className="h-8 w-8 text-slate-600 mb-4" />
            <h3 className="text-xl font-semibold text-slate-900 mb-3">Public Interest</h3>
            <p className="text-slate-700">
              Our work serves the legitimate public interest in police accountability
              and transparency in public order policing.
            </p>
          </Card>

          <Card className="p-6 border border-slate-200">
            <Mail className="h-8 w-8 text-slate-600 mb-4" />
            <h3 className="text-xl font-semibold text-slate-900 mb-3">Open Communication</h3>
            <p className="text-slate-700">
              We maintain transparent practices and welcome corrections to
              any inaccuracies in our documentation.
            </p>
          </Card>
        </div>

        {/* Methodology */}
        <div className="bg-white rounded-lg p-8 border border-slate-200 mb-12">
          <h2 className="text-2xl font-bold text-slate-900 mb-6">Our Methodology</h2>
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-slate-900 mb-2">Source Verification</h3>
              <p className="text-slate-700">
                We carefully verify all sources and cross-reference information from multiple
                publicly available materials including news reports, social media posts, and
                official statements.
              </p>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-slate-900 mb-2">Factual Documentation</h3>
              <p className="text-slate-700">
                Our documentation focuses on observable actions and verifiable facts, avoiding
                speculation, inflammatory language, or unsubstantiated claims.
              </p>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-slate-900 mb-2">Transparency</h3>
              <p className="text-slate-700">
                Every piece of information is linked to its original source, allowing visitors
                to examine the evidence and draw their own conclusions.
              </p>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-slate-900 mb-2">Professional Standards</h3>
              <p className="text-slate-700">
                We maintain professional, objective standards in all documentation while
                serving the public interest in police accountability.
              </p>
            </div>
          </div>
        </div>

        {/* Legal Notice */}
        <div className="bg-slate-100 rounded-lg p-8 mb-12">
          <h2 className="text-2xl font-bold text-slate-900 mb-4">Legal Framework</h2>
          <p className="text-slate-700 mb-4">
            Our activities are conducted in full compliance with UK law. We operate under the principles of:
          </p>
          <ul className="list-disc list-inside text-slate-700 space-y-2">
            <li>Human Rights Act 1998 protections for free expression and peaceful assembly</li>
            <li>Freedom of Information Act 2000 principles promoting government transparency</li>
            <li>Data Protection Act 2018 and UK GDPR compliance</li>
            <li>Ethical journalism standards for accurate, fair reporting</li>
          </ul>
        </div>

        {/* Contact Information */}
        <div className="text-center bg-white rounded-lg p-8 border border-slate-200">
          <h2 className="text-2xl font-bold text-slate-900 mb-4">Contribute</h2>
          <p className="text-slate-700 mb-6">
            We welcome contributions from individuals who share our commitment to transparency
            and evidence-based documentation of police conduct at public demonstrations.
          </p>
          <p className="text-sm text-slate-600">
            This is an independent research initiative. All data is collected from publicly
            available sources in accordance with UK law.
          </p>
        </div>
      </div>
    </div>
  );
};

export default About;

