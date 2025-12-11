import { Eye, Shield, FileText, Scale, Users, Database } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

const ManifestoPage = () => {
  return (
    <div className="min-h-screen bg-slate-50">
      {/* Hero Section */}
      <div className="bg-white border-b border-slate-200">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <div className="text-center">
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-slate-100 text-slate-600 text-sm font-medium rounded-full mb-6">
              <FileText className="h-4 w-4" />
              Our Methodology
            </div>
            <h1 className="text-4xl md:text-5xl font-bold text-slate-900 mb-6 tracking-tight">
              Our Approach to Documentation
            </h1>
            <p className="text-xl text-slate-600 max-w-3xl mx-auto leading-relaxed">
              A principled, transparent methodology for maintaining accurate records
              of police conduct at public demonstrations.
            </p>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16 space-y-16">

        {/* Principles Section */}
        <section>
          <h2 className="text-2xl font-bold text-slate-900 mb-8 text-center">
            Core Principles
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card className="p-6 bg-white border border-slate-200">
              <Eye className="h-8 w-8 text-slate-600 mb-4" />
              <h3 className="text-lg font-semibold text-slate-900 mb-2">Transparency</h3>
              <p className="text-slate-600 text-sm">
                All documented information is derived from publicly available sources.
                We maintain clear attribution and source links for verification.
              </p>
            </Card>

            <Card className="p-6 bg-white border border-slate-200">
              <Scale className="h-8 w-8 text-slate-600 mb-4" />
              <h3 className="text-lg font-semibold text-slate-900 mb-2">Objectivity</h3>
              <p className="text-slate-600 text-sm">
                Our documentation focuses on observable facts and verifiable
                information, avoiding speculation or editorializing.
              </p>
            </Card>

            <Card className="p-6 bg-white border border-slate-200">
              <Shield className="h-8 w-8 text-slate-600 mb-4" />
              <h3 className="text-lg font-semibold text-slate-900 mb-2">Accountability</h3>
              <p className="text-slate-600 text-sm">
                We believe that public servants acting in their official capacity
                should be accountable for their documented actions.
              </p>
            </Card>
          </div>
        </section>

        {/* Methodology Section */}
        <section className="bg-white rounded-lg p-8 border border-slate-200">
          <h2 className="text-2xl font-bold text-slate-900 mb-6">
            Documentation Methodology
          </h2>
          <div className="space-y-6">
            <div className="flex items-start gap-4">
              <div className="w-8 h-8 bg-slate-100 rounded-full flex items-center justify-center flex-shrink-0">
                <span className="text-slate-700 font-semibold text-sm">1</span>
              </div>
              <div>
                <h4 className="font-semibold text-slate-900 mb-1">Evidence Collection</h4>
                <p className="text-slate-600 text-sm">
                  Media is collected exclusively from public sources: social media posts,
                  news coverage, and publicly shared photographs and videos from demonstrations.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-4">
              <div className="w-8 h-8 bg-slate-100 rounded-full flex items-center justify-center flex-shrink-0">
                <span className="text-slate-700 font-semibold text-sm">2</span>
              </div>
              <div>
                <h4 className="font-semibold text-slate-900 mb-1">Verification Process</h4>
                <p className="text-slate-600 text-sm">
                  Each piece of evidence undergoes verification to confirm its authenticity,
                  date, location, and context before being added to the database.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-4">
              <div className="w-8 h-8 bg-slate-100 rounded-full flex items-center justify-center flex-shrink-0">
                <span className="text-slate-700 font-semibold text-sm">3</span>
              </div>
              <div>
                <h4 className="font-semibold text-slate-900 mb-1">Officer Identification</h4>
                <p className="text-slate-600 text-sm">
                  Officers are identified by visible badge numbers, shoulder numbers,
                  and official insignia visible in the documentation.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-4">
              <div className="w-8 h-8 bg-slate-100 rounded-full flex items-center justify-center flex-shrink-0">
                <span className="text-slate-700 font-semibold text-sm">4</span>
              </div>
              <div>
                <h4 className="font-semibold text-slate-900 mb-1">Database Entry</h4>
                <p className="text-slate-600 text-sm">
                  Verified information is catalogued with full source attribution,
                  allowing independent verification of all documented incidents.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Data Handling Section */}
        <section>
          <h2 className="text-2xl font-bold text-slate-900 mb-6 text-center">
            Data Handling Standards
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card className="p-6 bg-white border border-slate-200">
              <Database className="h-6 w-6 text-slate-600 mb-3" />
              <h4 className="font-semibold text-slate-900 mb-2">Public Information Only</h4>
              <p className="text-slate-600 text-sm">
                We only document information that is already in the public domain.
                No private information is collected or published.
              </p>
            </Card>

            <Card className="p-6 bg-white border border-slate-200">
              <FileText className="h-6 w-6 text-slate-600 mb-3" />
              <h4 className="font-semibold text-slate-900 mb-2">Source Attribution</h4>
              <p className="text-slate-600 text-sm">
                Every piece of documentation includes links to original sources,
                enabling independent verification.
              </p>
            </Card>

            <Card className="p-6 bg-white border border-slate-200">
              <Shield className="h-6 w-6 text-slate-600 mb-3" />
              <h4 className="font-semibold text-slate-900 mb-2">Legal Compliance</h4>
              <p className="text-slate-600 text-sm">
                All operations comply with UK data protection law and the
                legitimate public interest in police accountability.
              </p>
            </Card>

            <Card className="p-6 bg-white border border-slate-200">
              <Users className="h-6 w-6 text-slate-600 mb-3" />
              <h4 className="font-semibold text-slate-900 mb-2">Correction Process</h4>
              <p className="text-slate-600 text-sm">
                Errors in documentation can be reported and will be investigated
                and corrected in a timely manner.
              </p>
            </Card>
          </div>
        </section>

        {/* Call to Action */}
        <section className="text-center bg-white rounded-lg p-8 border border-slate-200">
          <h2 className="text-2xl font-bold text-slate-900 mb-4">
            Contribute to the Record
          </h2>
          <p className="text-slate-600 mb-6 max-w-2xl mx-auto">
            If you have documented evidence from public demonstrations that meets
            our standards, we welcome your contribution to this public record.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link to="/register">
              <Button className="bg-slate-900 hover:bg-slate-800 text-white">
                Create Account
              </Button>
            </Link>
            <Link to="/about">
              <Button variant="outline" className="border-slate-300">
                Learn More
              </Button>
            </Link>
          </div>
        </section>

      </div>
    </div>
  );
};

export default ManifestoPage;
