import { useState, useEffect } from 'react';
import { Shield, ShieldAlert, Radio, Camera, Link2, Loader2, ChevronRight, X } from 'lucide-react';
import { Button } from '@/components/ui/button';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Helper to handle both absolute R2 URLs and relative API paths
const getImageUrl = (url) => {
    if (!url) return '';
    if (url.startsWith('http://') || url.startsWith('https://')) {
        return url;
    }
    return `${API_BASE}${url}`;
};

// Category icons and colors
const CATEGORY_CONFIG = {
  defensive: {
    icon: Shield,
    color: 'bg-blue-500',
    lightBg: 'bg-blue-50',
    textColor: 'text-blue-700',
    borderColor: 'border-blue-200',
    label: 'Defensive'
  },
  offensive: {
    icon: ShieldAlert,
    color: 'bg-red-500',
    lightBg: 'bg-red-50',
    textColor: 'text-red-700',
    borderColor: 'border-red-200',
    label: 'Offensive'
  },
  restraint: {
    icon: Link2,
    color: 'bg-orange-500',
    lightBg: 'bg-orange-50',
    textColor: 'text-orange-700',
    borderColor: 'border-orange-200',
    label: 'Restraint'
  },
  identification: {
    icon: Camera,
    color: 'bg-green-500',
    lightBg: 'bg-green-50',
    textColor: 'text-green-700',
    borderColor: 'border-green-200',
    label: 'Identification'
  },
  communication: {
    icon: Radio,
    color: 'bg-purple-500',
    lightBg: 'bg-purple-50',
    textColor: 'text-purple-700',
    borderColor: 'border-purple-200',
    label: 'Communication'
  },
  specialist: {
    icon: Shield,
    color: 'bg-gray-500',
    lightBg: 'bg-gray-50',
    textColor: 'text-gray-700',
    borderColor: 'border-gray-200',
    label: 'Specialist'
  }
};

const EquipmentCard = ({ equipment, onClick }) => {
  const config = CATEGORY_CONFIG[equipment.category] || CATEGORY_CONFIG.specialist;
  const Icon = config.icon;

  return (
    <div
      onClick={() => onClick(equipment)}
      className={`${config.lightBg} ${config.borderColor} border rounded-lg p-4 cursor-pointer hover:shadow-md transition-all`}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className={`${config.color} p-2 rounded-lg`}>
            <Icon className="h-5 w-5 text-white" />
          </div>
          <div>
            <h3 className={`font-medium ${config.textColor}`}>{equipment.name}</h3>
            <p className="text-xs text-gray-500 capitalize">{config.label}</p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <span className={`${config.color} text-white text-xs px-2 py-1 rounded-full font-medium`}>
            {equipment.detection_count}
          </span>
          <ChevronRight className="h-4 w-4 text-gray-400" />
        </div>
      </div>
      {equipment.description && (
        <p className="text-xs text-gray-600 mt-2 line-clamp-2">{equipment.description}</p>
      )}
    </div>
  );
};

const DetectionModal = ({ equipment, onClose }) => {
  const [detections, setDetections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchDetections = async () => {
      try {
        const res = await fetch(`${API_BASE}/equipment/${equipment.id}/detections`);
        const data = await res.json();
        setDetections(data.detections || []);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    };
    fetchDetections();
  }, [equipment.id]);

  const config = CATEGORY_CONFIG[equipment.category] || CATEGORY_CONFIG.specialist;

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl max-w-2xl w-full max-h-[80vh] overflow-hidden">
        {/* Header */}
        <div className={`${config.color} text-white p-4`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <config.icon className="h-6 w-6" />
              <div>
                <h2 className="font-bold text-lg">{equipment.name}</h2>
                <p className="text-sm text-white/80">{equipment.description}</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1 hover:bg-white/20 rounded"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-4 overflow-y-auto max-h-[60vh]">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
            </div>
          ) : error ? (
            <div className="text-center py-8 text-red-600">
              Error loading detections: {error}
            </div>
          ) : detections.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              No detections found for this equipment.
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-sm text-gray-600 mb-4">
                Found in {detections.length} officer appearance{detections.length !== 1 ? 's' : ''}
              </p>
              {detections.map((det, idx) => (
                <div
                  key={idx}
                  className="border rounded-lg p-3 flex items-center gap-4 hover:bg-gray-50"
                >
                  {det.crop_path ? (
                    <img
                      src={getImageUrl(det.crop_path)}
                      alt="Officer"
                      className="w-16 h-16 object-cover rounded"
                    />
                  ) : (
                    <div className="w-16 h-16 bg-gray-200 rounded flex items-center justify-center">
                      <Shield className="h-6 w-6 text-gray-400" />
                    </div>
                  )}
                  <div className="flex-1">
                    <div className="font-medium text-sm">
                      Officer #{det.officer_id}
                      {det.badge_number && ` - ${det.badge_number}`}
                    </div>
                    {det.force && (
                      <div className="text-xs text-gray-500">{det.force}</div>
                    )}
                    {det.timestamp && (
                      <div className="text-xs text-gray-400">@ {det.timestamp}</div>
                    )}
                  </div>
                  {det.confidence && (
                    <div className={`text-xs px-2 py-1 rounded ${
                      det.confidence >= 0.8 ? 'bg-green-100 text-green-700' :
                      det.confidence >= 0.5 ? 'bg-yellow-100 text-yellow-700' :
                      'bg-red-100 text-red-700'
                    }`}>
                      {Math.round(det.confidence * 100)}%
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const EquipmentPage = () => {
  const [equipment, setEquipment] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedEquipment, setSelectedEquipment] = useState(null);

  useEffect(() => {
    const fetchEquipment = async () => {
      try {
        const url = selectedCategory
          ? `${API_BASE}/equipment?category=${selectedCategory}`
          : `${API_BASE}/equipment`;
        const res = await fetch(url);
        const data = await res.json();
        setEquipment(data.equipment || []);
        if (data.categories) setCategories(data.categories);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    };
    fetchEquipment();
  }, [selectedCategory]);

  // Group equipment by category
  const groupedEquipment = equipment.reduce((acc, item) => {
    const cat = item.category || 'specialist';
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(item);
    return acc;
  }, {});

  // Calculate total detections
  const totalDetections = equipment.reduce((sum, e) => sum + e.detection_count, 0);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Equipment Database</h1>
        <p className="text-gray-600">
          Police equipment detected across all analyzed footage.
          Click an item to see all officers detected with that equipment.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-white rounded-lg border p-4">
          <div className="text-2xl font-bold text-gray-900">{equipment.length}</div>
          <div className="text-sm text-gray-500">Equipment Types</div>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <div className="text-2xl font-bold text-gray-900">{categories.length}</div>
          <div className="text-sm text-gray-500">Categories</div>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <div className="text-2xl font-bold text-green-600">{totalDetections}</div>
          <div className="text-sm text-gray-500">Total Detections</div>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <div className="text-2xl font-bold text-blue-600">
            {equipment.filter(e => e.detection_count > 0).length}
          </div>
          <div className="text-sm text-gray-500">Items Detected</div>
        </div>
      </div>

      {/* Category Filter */}
      <div className="flex flex-wrap gap-2 mb-6">
        <Button
          variant={selectedCategory === null ? 'default' : 'outline'}
          size="sm"
          onClick={() => setSelectedCategory(null)}
        >
          All Categories
        </Button>
        {categories.map(cat => {
          const config = CATEGORY_CONFIG[cat] || CATEGORY_CONFIG.specialist;
          return (
            <Button
              key={cat}
              variant={selectedCategory === cat ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedCategory(cat)}
              className={selectedCategory === cat ? config.color : ''}
            >
              {config.label}
            </Button>
          );
        })}
      </div>

      {/* Loading/Error states */}
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
        </div>
      ) : error ? (
        <div className="text-center py-16 text-red-600">
          Error loading equipment: {error}
        </div>
      ) : selectedCategory ? (
        /* Single category view */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {equipment.map(item => (
            <EquipmentCard
              key={item.id}
              equipment={item}
              onClick={setSelectedEquipment}
            />
          ))}
        </div>
      ) : (
        /* Grouped by category view */
        <div className="space-y-8">
          {Object.entries(groupedEquipment).map(([category, items]) => {
            const config = CATEGORY_CONFIG[category] || CATEGORY_CONFIG.specialist;
            return (
              <div key={category}>
                <div className="flex items-center gap-2 mb-4">
                  <div className={`${config.color} p-1.5 rounded`}>
                    <config.icon className="h-4 w-4 text-white" />
                  </div>
                  <h2 className="text-lg font-bold text-gray-900">{config.label}</h2>
                  <span className="text-sm text-gray-500">({items.length} items)</span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {items.map(item => (
                    <EquipmentCard
                      key={item.id}
                      equipment={item}
                      onClick={setSelectedEquipment}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Detection Modal */}
      {selectedEquipment && (
        <DetectionModal
          equipment={selectedEquipment}
          onClose={() => setSelectedEquipment(null)}
        />
      )}
    </div>
  );
};

export default EquipmentPage;
