import { Mail, Globe, Users, Heart } from 'lucide-react';
import { Card } from '@/components/ui/card';

const About = () => {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Hero Section */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <div className="text-center">
            <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-6">
              About Us
            </h1>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              A grassroots initiative dedicated to promoting transparency, accountability, 
              and the protection of constitutional rights.
            </p>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        {/* Mission Statement */}
        <div className="bg-white rounded-lg p-8 shadow-md mb-12">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Our Mission</h2>
          <p className="text-lg text-gray-700 leading-relaxed mb-6">
            The Accountability Campaign is a community-driven initiative focused on documenting 
            police interactions during peaceful demonstrations. We believe that transparency and 
            factual documentation serve the interests of both law enforcement and the communities 
            they protect.
          </p>
          <p className="text-lg text-gray-700 leading-relaxed">
            Our work is grounded in respect for constitutional rights, democratic principles, 
            and the belief that accountability strengthens rather than undermines effective 
            law enforcement.
          </p>
        </div>

        {/* Values */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-12">
          <Card className="p-6">
            <Users className="h-8 w-8 text-blue-600 mb-4" />
            <h3 className="text-xl font-semibold text-gray-900 mb-3">Community-Centered</h3>
            <p className="text-gray-700">
              We are a grassroots organization driven by community members who believe in 
              the power of civic engagement and peaceful advocacy.
            </p>
          </Card>
          
          <Card className="p-6">
            <Globe className="h-8 w-8 text-blue-600 mb-4" />
            <h3 className="text-xl font-semibold text-gray-900 mb-3">Evidence-Based</h3>
            <p className="text-gray-700">
              All our documentation relies on publicly available sources and verifiable 
              information, ensuring accuracy and credibility.
            </p>
          </Card>
          
          <Card className="p-6">
            <Heart className="h-8 w-8 text-blue-600 mb-4" />
            <h3 className="text-xl font-semibold text-gray-900 mb-3">Peaceful Advocacy</h3>
            <p className="text-gray-700">
              We are committed to non-violent, legal methods of advocacy that respect 
              democratic processes and constitutional principles.
            </p>
          </Card>
          
          <Card className="p-6">
            <Mail className="h-8 w-8 text-blue-600 mb-4" />
            <h3 className="text-xl font-semibold text-gray-900 mb-3">Open Communication</h3>
            <p className="text-gray-700">
              We believe in dialogue, transparency, and working constructively with all 
              stakeholders to improve community-police relations.
            </p>
          </Card>
        </div>

        {/* Methodology */}
        <div className="bg-white rounded-lg p-8 shadow-md mb-12">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Our Methodology</h2>
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Source Verification</h3>
              <p className="text-gray-700">
                We carefully verify all sources and cross-reference information from multiple 
                publicly available materials including news reports, social media posts, and 
                official statements.
              </p>
            </div>
            
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Factual Documentation</h3>
              <p className="text-gray-700">
                Our documentation focuses on observable actions and verifiable facts, avoiding 
                speculation, inflammatory language, or unsubstantiated claims.
              </p>
            </div>
            
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Transparency</h3>
              <p className="text-gray-700">
                Every piece of information is linked to its original source, allowing visitors 
                to examine the evidence and draw their own conclusions.
              </p>
            </div>
            
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Respectful Presentation</h3>
              <p className="text-gray-700">
                We maintain a professional, respectful tone in all our communications while 
                advocating for transparency and accountability.
              </p>
            </div>
          </div>
        </div>

        {/* Legal Notice */}
        <div className="bg-blue-50 rounded-lg p-8 mb-12">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Legal Framework</h2>
          <p className="text-gray-700 mb-4">
            Our activities are conducted in full compliance with applicable laws and constitutional 
            protections. We operate under the principles of:
          </p>
          <ul className="list-disc list-inside text-gray-700 space-y-2">
            <li>First Amendment protections for free speech and peaceful assembly</li>
            <li>Freedom of Information Act principles promoting government transparency</li>
            <li>Public records laws ensuring community access to information</li>
            <li>Ethical journalism standards for accurate, fair reporting</li>
          </ul>
        </div>

        {/* Contact Information */}
        <div className="text-center bg-white rounded-lg p-8 shadow-md">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Get Involved</h2>
          <p className="text-gray-700 mb-6">
            We welcome community members who share our commitment to transparency, accountability, 
            and constitutional rights. Join us in building a more just and transparent society.
          </p>
          <p className="text-sm text-gray-600">
            This is a volunteer-driven initiative. We do not accept donations or engage in 
            partisan political activities.
          </p>
        </div>
      </div>
    </div>
  );
};

export default About;

