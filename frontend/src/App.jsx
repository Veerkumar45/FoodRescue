
import React, { useCallback, useEffect, useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid
} from 'recharts';

const API = 'http://127.0.0.1:8000';

async function get(path) {
  const response = await fetch(API + path);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

async function post(path, data) {
  const response = await fetch(API + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });

  const result = await response.json();

  if (!response.ok) {
    throw new Error(
      result.detail?.message || result.detail || 'Request failed'
    );
  }

  return result;
}

async function remove(path) {
  const response = await fetch(API + path, {
    method: 'DELETE'
  });

  const result = await response.json();

  if (!response.ok) {
    throw new Error(
      result.detail?.message || result.detail || 'Delete failed'
    );
  }

  return result;
}

const nav = [
  { name: 'Overview', icon: '⌂' },
  { name: 'Inventory', icon: '🥬' },
  { name: 'Predictions', icon: '◈' },
  { name: 'Donations', icon: '♡' },
  { name: 'Analytics', icon: '▥' },
  { name: 'Pipeline Monitor', icon: '⌁' }
];

const number = value =>
  Number(value || 0).toLocaleString('en-IN');

const foodImages = {
  eggs: 'https://images.unsplash.com/photo-1506976785307-8732e854ad03?auto=format&fit=crop&w=600&q=80',
  juice: 'https://images.pexels.com/photos/38956011/pexels-photo-38956011.jpeg',
  rice: 'https://etimg.etb2bimg.com/photo/86109886.cms',
  wheat: 'https://images.unsplash.com/photo-1764070254247-351def349875?auto=format&fit=crop&w=600&q=80',
  bakery: 'https://images.unsplash.com/photo-1509440159596-0249088772ff?w=600',
  apple: 'https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?w=600',
  banana: 'https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?w=600',
  fruit: 'https://images.unsplash.com/photo-1610832958506-aa56368176cf?w=600',
  vegetable: 'https://images.unsplash.com/photo-1540420773420-3366772f4999?w=600',
  milk: 'https://images.unsplash.com/photo-1563636619-e9143da7973b?w=600',
  yogurt: 'https://images.unsplash.com/photo-1488477181946-6428a0291777?w=600',
  default: 'https://images.unsplash.com/photo-1542838132-92c53300491e?w=600'
};

function imageFor(name = '', category = '') {
  const product = String(name).toLowerCase().trim();
  const type = String(category).toLowerCase().trim();

  if (/\beggs?\b/.test(product)) return foodImages.eggs;

  if (
    product.includes('juice') ||
    product.includes('orange drink')
  ) {
    return foodImages.juice;
  }

  if (/\brice\b/.test(product)) return foodImages.rice;

  if (
    product.includes('wheat') ||
    product.includes('flour')
  ) {
    return foodImages.wheat;
  }

  if (product.includes('apple')) return foodImages.apple;
  if (product.includes('banana')) return foodImages.banana;

  if (
    product.includes('yogurt') ||
    product.includes('yoghurt') ||
    product.includes('curd')
  ) {
    return foodImages.yogurt;
  }

  if (product.includes('milk')) return foodImages.milk;

  if (
    type.includes('bakery') ||
    type.includes('bread')
  ) {
    return foodImages.bakery;
  }

  if (type.includes('fruit')) return foodImages.fruit;

  if (
    type.includes('vegetable') ||
    type.includes('produce')
  ) {
    return foodImages.vegetable;
  }

  if (type.includes('dairy')) return foodImages.milk;

  return foodImages.default;
}

function ProductImage({ name, category, className = '' }) {
  const [failed, setFailed] = useState(false);

  const src = failed
    ? foodImages.default
    : imageFor(name, category);

  return (
    <img
      className={className}
      src={src}
      alt={name || 'Food product'}
      onError={() => setFailed(true)}
    />
  );
}

function Badge({ value }) {
  const label = value ?? 'Unknown';

  const tone = String(label)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-');

  return (
    <span className={`badge badge-${tone}`}>
      {label}
    </span>
  );
}

function StatCard({
  label,
  value,
  helper,
  icon,
  tone = 'green'
}) {
  return (
    <article className={`stat-card stat-${tone}`}>
      <div className="stat-topline">
        <span className="stat-label">{label}</span>
        <span className="stat-icon">{icon}</span>
      </div>

      <strong className="stat-value">
        {number(value)}
      </strong>

      <span className="stat-helper">{helper}</span>
    </article>
  );
}

function Panel({
  title,
  subtitle,
  action,
  children,
  className = ''
}) {
  return (
    <section className={`panel ${className}`}>
      {(title || action) && (
        <div className="panel-header">
          <div>
            {title && <h2>{title}</h2>}
            {subtitle && <p>{subtitle}</p>}
          </div>

          {action}
        </div>
      )}

      {children}
    </section>
  );
}

function DataTable({ columns, rows }) {
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            {columns.map(column => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>

        <tbody>
          {rows.length ? (
            rows.map((row, index) => (
              <tr key={index}>
                {row.map((cell, cellIndex) => (
                  <td key={cellIndex}>{cell}</td>
                ))}
              </tr>
            ))
          ) : (
            <tr>
              <td
                colSpan={columns.length}
                className="empty-cell"
              >
                No records found yet
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function App() {
  const [page, setPage] = useState('Overview');

  const [summary, setSummary] = useState({});
  const [inventory, setInventory] = useState([]);
  const [predictions, setPredictions] = useState([]);
  const [donations, setDonations] = useState([]);
  const [ngos, setNgos] = useState([]);
  const [runs, setRuns] = useState([]);
  const [quality, setQuality] = useState({});
  const [daily, setDaily] = useState([]);

  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);

  const [form, setForm] = useState({
    product_id: 'PROD_006',
    name: '',
    category: 'Bakery',
    unit: 'pack',
    expiry_date: new Date(
      Date.now() + 7 * 86400000
    ).toISOString().slice(0, 10),
    quantity: 10
  });

  const [sale, setSale] = useState({
    product_id: 'PROD_001',
    quantity: 1
  });

  const [donation, setDonation] = useState({
    product_id: 'PROD_001',
    quantity: 1,
    note: 'Surplus donation'
  });

  const refresh = useCallback(async (showLoader = false) => {
    if (showLoader) setLoading(true);

    try {
      const [
        s, i, p, d, n, r, q, a
      ] = await Promise.all([
        get('/api/dashboard/summary'),
        get('/api/inventory'),
        get('/api/predictions'),
        get('/api/donations'),
        get('/api/ngos'),
        get('/api/pipeline/runs'),
        get('/api/pipeline/quality'),
        get('/api/analytics/daily')
      ]);

      setSummary(s);
      setInventory(i);
      setPredictions(p);
      setDonations(d);
      setNgos(n);
      setRuns(r);
      setQuality(q);
      setDaily(a);

      setError('');
      setLastUpdated(new Date());
    } catch (err) {
      setError(
        'Unable to connect to FoodRescue API. ' +
        'Make sure FastAPI is running at http://127.0.0.1:8000. ' +
        err.message
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh(true);

    const interval = setInterval(
      () => refresh(false),
      10000
    );

    return () => clearInterval(interval);
  }, [refresh]);

  const perform = async callback => {
    try {
      setError('');
      setNotice('');

      const message = await callback();

      setNotice(
        message || 'Action completed successfully.'
      );

      await refresh(false);
    } catch (err) {
      setError(String(err.message || err));
    }
  };

  const deleteProduct = product => {
    const confirmed = window.confirm(
      `Are you sure you want to delete ${product.name}?`
    );

    if (!confirmed) return;

    perform(async () => {
      const result = await remove(
        `/api/inventory/${encodeURIComponent(product.product_id)}`
      );

      return result.message || 'Product deleted successfully.';
    });
  };

  const verifyProduct = product => {
    perform(async () => {
      const params = new URLSearchParams({
        verifier_name: 'FreshMart Store Admin',
        verifier_role: 'admin'
      });

      const response = await fetch(
        `${API}/api/products/${encodeURIComponent(product.product_id)}/verify?${params}`,
        { method: 'POST' }
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(
          result.detail?.message ||
          result.detail ||
          'Verification failed'
        );
      }

      return result.message || 'Food verified successfully.';
    });
  };

  const deleteDonation = donationItem => {
    const confirmed = window.confirm(
      `Delete donation ${donationItem.donation_id}? ` +
      'Its quantity will be returned to inventory.'
    );

    if (!confirmed) return;

    perform(async () => {
      const result = await remove(
        `/api/donations/${encodeURIComponent(donationItem.donation_id)}`
      );

      return result.message ||
        'Donation deleted and inventory stock restored.';
    });
  };

  const changePage = name => {
    setPage(name);
    setNotice('');
    setError('');
  };

  const inventoryOptions = inventory.map(item => (
    <option
      key={item.product_id}
      value={item.product_id}
    >
      {item.name} · {item.quantity} {item.unit}
    </option>
  ));

  const pageDescriptions = {
    Overview: 'A little more food saved, a little less food wasted.',
    Inventory: 'Keep track of every fresh product in your store.',
    Predictions: 'Spot surplus early and give good food another chance.',
    Donations: 'Connect surplus food with people who need it.',
    Analytics: 'See the positive impact of smarter food management.',
    'Pipeline Monitor': 'Keep your food data flowing accurately.'
  };

  const renderOverview = () => (
    <>
      <section className="welcome-banner">
        <div className="welcome-copy">
          <span className="welcome-tag">
            🌱 FRESH FOOD. BETTER FUTURE.
          </span>

          <h2>
            Good food deserves<br />
            a second chance.
          </h2>

          <p>
            Track freshness, prevent food waste and help surplus food
            reach communities that need it.
          </p>

          <button
            className="banner-button"
            onClick={() => changePage('Inventory')}
          >
            Explore inventory <span>→</span>
          </button>
        </div>

        <div className="welcome-art">
          <img
            src="https://images.unsplash.com/photo-1542838132-92c53300491e?w=900"
            alt="Fresh vegetables and produce"
          />

          <div className="floating-note">
            <span>🥑</span>

            <div>
              <strong>Freshness first</strong>
              <small>Waste less, share more</small>
            </div>
          </div>
        </div>

        <div className="banner-decoration">✳</div>
      </section>

      <div className="section-heading">
        <div>
          <span className="section-kicker">
            YOUR STORE AT A GLANCE
          </span>

          <h2>Today's overview</h2>
        </div>

        <span className="soft-label">Live store data</span>
      </div>

      <div className="stats-grid">
        <StatCard
          label="Inventory units"
          value={summary.total_inventory}
          helper="Units currently in stock"
          icon="📦"
        />

        <StatCard
          label="Potential surplus"
          value={summary.surplus_units}
          helper="Estimated excess stock"
          icon="🥕"
          tone="yellow"
        />

        <StatCard
          label="At-risk products"
          value={summary.at_risk_products}
          helper="Products needing attention"
          icon="⏳"
          tone="pink"
        />

        <StatCard
          label="Redistributed units"
          value={summary.redistributed_units}
          helper="Accepted, collected or delivered"
          icon="💚"
          tone="blue"
        />
      </div>

      <div className="two-column">
        <Panel
          title="Freshness watch"
          subtitle="Products that may need your attention"
          action={
            <button
              className="text-button"
              onClick={() => changePage('Predictions')}
            >
              View all →
            </button>
          }
        >
          {predictions
            .filter(item => item.risk !== 'Low')
            .slice(0, 5).length ? (
              predictions
                .filter(item => item.risk !== 'Low')
                .slice(0, 5)
                .map(item => (
                  <div
                    className="freshness-row"
                    key={item.product_id}
                  >
                    <ProductImage
                      name={item.name}
                      category={item.category}
                    />

                    <div className="freshness-info">
                      <strong>{item.name}</strong>

                      <span>
                        {item.quantity} {item.unit} available ·
                        Expires {item.expiry_date}
                      </span>
                    </div>

                    <Badge value={item.risk} />
                  </div>
                ))
            ) : (
              <div className="empty-state">
                <span>🌿</span>
                <strong>No urgent risks detected</strong>
                <p>
                  Products requiring attention will appear here.
                </p>
              </div>
            )}
        </Panel>

        <Panel
          title="Food rescue activity"
          subtitle="Latest data processing batches"
          action={
            <button
              className="text-button"
              onClick={() => changePage('Pipeline Monitor')}
            >
              Open monitor →
            </button>
          }
        >
          {runs.slice(0, 4).length ? (
            runs.slice(0, 4).map(run => (
              <div
                className="activity-item"
                key={run.run_id}
              >
                <span className="activity-icon">🌱</span>

                <div className="activity-info">
                  <strong>{run.batch_id}</strong>

                  <span>
                    {run.processed} processed ·
                    {run.rejected} rejected
                  </span>
                </div>

                <Badge value={run.status} />
              </div>
            ))
          ) : (
            <div className="empty-state">
              <span>📊</span>
              <strong>No processing runs yet</strong>
              <p>
                Generate a sample batch from Pipeline Monitor.
              </p>
            </div>
          )}
        </Panel>
      </div>

      <Panel
        title="A look inside your inventory"
        subtitle="Fresh products currently registered in your store"
        action={
          <button
            className="text-button"
            onClick={() => changePage('Inventory')}
          >
            Manage inventory →
          </button>
        }
      >
        <div className="product-grid">
          {inventory.slice(0, 4).map(item => (
            <article
              className="product-card"
              key={item.product_id}
            >
              <div className="product-image">
                <ProductImage
                  name={item.name}
                  category={item.category}
                />

                <span className="product-category">
                  {item.category}
                </span>
              </div>

              <div className="product-card-body">
                <strong>{item.name}</strong>

                <span>
                  {item.quantity} {item.unit} available
                </span>

                <div className="product-card-bottom">
                  <small>Expiry: {item.expiry_date}</small>
                  <Badge value={item.safety_status} />
                </div>
              </div>
            </article>
          ))}

          {!inventory.length && (
            <div className="empty-state">
              Add products to see your inventory here.
            </div>
          )}
        </div>
      </Panel>

      <section className="impact-banner">
        <div className="impact-leaf">🌍</div>

        <div>
          <span>SMALL ACTIONS. BIGGER IMPACT.</span>

          <h2>
            Every rescued item is a step towards less waste.
          </h2>

          <p>
            FoodRescue helps businesses identify surplus and
            coordinate redistribution.
          </p>
        </div>

        <button onClick={() => changePage('Donations')}>
          Explore donations →
        </button>
      </section>
    </>
  );

  const renderInventory = () => (
    <>
      <div className="section-heading">
        <div>
          <span className="section-kicker">
            FRESH STOCK MANAGEMENT
          </span>

          <h2>Your product collection</h2>
        </div>

        <span className="soft-label">
          {inventory.length} products tracked
        </span>
      </div>

      <Panel
        title="Add a fresh product"
        subtitle="Register a product and its opening stock."
      >
        <form
          className="form-grid"
          onSubmit={event => {
            event.preventDefault();

            perform(async () => {
              const result = await post('/api/inventory', {
                ...form,
                quantity: Number(form.quantity)
              });

              return result.message || 'Product added successfully.';
            });
          }}
        >
          <label>
            Product ID
            <input
              required
              value={form.product_id}
              onChange={e =>
                setForm({
                  ...form,
                  product_id: e.target.value
                })
              }
            />
          </label>

          <label>
            Product name
            <input
              required
              placeholder="e.g. Whole wheat bread"
              value={form.name}
              onChange={e =>
                setForm({
                  ...form,
                  name: e.target.value
                })
              }
            />
          </label>

          <label>
            Category
            <input
              required
              value={form.category}
              onChange={e =>
                setForm({
                  ...form,
                  category: e.target.value
                })
              }
            />
          </label>

          <label>
            Unit
            <input
              required
              value={form.unit}
              onChange={e =>
                setForm({
                  ...form,
                  unit: e.target.value
                })
              }
            />
          </label>

          <label>
            Expiry date
            <input
              required
              type="date"
              value={form.expiry_date}
              onChange={e =>
                setForm({
                  ...form,
                  expiry_date: e.target.value
                })
              }
            />
          </label>

          <label>
            Opening quantity
            <input
              required
              type="number"
              min="1"
              value={form.quantity}
              onChange={e =>
                setForm({
                  ...form,
                  quantity: e.target.value
                })
              }
            />
          </label>

          <div className="form-actions">
            <button
              className="primary-button"
              type="submit"
            >
              ＋ Add product
            </button>
          </div>
        </form>
      </Panel>

      <Panel
        title="Record a sale"
        subtitle="Update stock by submitting a sales event."
      >
        <form
          className="form-grid"
          onSubmit={event => {
            event.preventDefault();

            perform(async () => {
              const result = await post('/api/sales', {
                event_id: 'SALE_' + Date.now(),
                product_id: sale.product_id,
                quantity: Number(sale.quantity),
                event_timestamp: new Date().toISOString()
              });

              return `Sale processed: ${result.processed} event(s).`;
            });
          }}
        >
          <label>
            Product
            <select
              required
              value={sale.product_id}
              onChange={e =>
                setSale({
                  ...sale,
                  product_id: e.target.value
                })
              }
            >
              {inventoryOptions}
            </select>
          </label>

          <label>
            Quantity
            <input
              type="number"
              min="1"
              required
              value={sale.quantity}
              onChange={e =>
                setSale({
                  ...sale,
                  quantity: e.target.value
                })
              }
            />
          </label>

          <div className="form-actions">
            <button
              className="primary-button"
              type="submit"
            >
              ↗ Record sale
            </button>
          </div>
        </form>
      </Panel>

      <Panel
        title="All inventory products"
        subtitle="Browse your current stock and safety status."
      >
        <div className="table-product-list">
          {inventory.map(item => (
            <div
              className="inventory-product-row"
              key={item.product_id}
            >
              <ProductImage
                name={item.name}
                category={item.category}
              />

              <div className="inventory-product-info">
                <strong>{item.name}</strong>

                <span>
                  {item.product_id} · {item.category}
                </span>
              </div>

              <div className="inventory-quantity">
                <strong>{item.quantity}</strong>
                <span>{item.unit}</span>
              </div>

              <div className="inventory-expiry">
                <span>Expiry date</span>
                <strong>{item.expiry_date}</strong>
              </div>

              <div className="inventory-actions">
                <Badge value={item.safety_status} />

                {String(item.safety_status).toLowerCase() !== 'verified' && (
                  <button
                    className="verify-button"
                    onClick={() => verifyProduct(item)}
                  >
                    ✓ Verify
                  </button>
                )}

                <button
                  className="delete-button"
                  onClick={() => deleteProduct(item)}
                >
                  Delete
                </button>
              </div>
            </div>
          ))}

          {!inventory.length && (
            <div className="empty-state">
              No inventory products found.
            </div>
          )}
        </div>
      </Panel>
    </>
  );

  const renderPredictions = () => (
    <>
      <div className="section-heading">
        <div>
          <span className="section-kicker">
            PREVENT WASTE BEFORE IT HAPPENS
          </span>

          <h2>Freshness predictions</h2>
        </div>

        <span className="soft-label">
          {predictions.length} products analysed
        </span>
      </div>

      <div className="prediction-banner">
        <span>💡</span>

        <div>
          <strong>
            Early warning for potential food waste
          </strong>

          <p>
            These are rule-based risk estimates using stock levels
            and expiry windows, not predictions from a trained
            machine-learning model. Review each product before
            taking action.
          </p>
        </div>
      </div>

      <Panel
        title="Products needing attention"
        subtitle="Review stock, expiry dates and estimated surplus."
      >
        <DataTable
          columns={[
            'PRODUCT',
            'CURRENT STOCK',
            'EXPIRY DATE',
            'DAYS LEFT',
            'RISK',
            'POTENTIAL SURPLUS',
            'REASON'
          ]}
          rows={predictions.map(item => [
            <strong className="table-product">
              {item.name}
            </strong>,
            `${item.quantity} ${item.unit}`,
            item.expiry_date,
            item.days_to_expiry,
            <Badge value={item.risk} />,
            item.surplus_quantity,
            (item.reasons || []).join('; ') ||
              'No current trigger'
          ])}
        />

        <p className="footnote">
          Risk thresholds are demonstration settings and should be
          calibrated for each product category. A risk score does
          not establish food safety or donation eligibility.
        </p>
      </Panel>
    </>
  );

  const renderDonations = () => (
    <>
      <section className="donation-hero">
        <div>
          <span className="section-kicker">
            SHARE GOODNESS
          </span>

          <h2>
            Rescue food.<br />
            Spread hope.
          </h2>

          <p>
            Help surplus food find a new destination through
            community partners.
          </p>
        </div>

        <img
          src="https://images.unsplash.com/photo-1593113598332-cd288d649433?w=700"
          alt="Food donation and community support"
        />
      </section>

      <Panel
        title="Create a donation request"
        subtitle="Submit surplus stock for review and redistribution."
      >
        <div className="prediction-banner">
          <span>♥</span>

          <div>
            <strong>Food safety comes first</strong>

            <p>
              Only products verified by an authorized person and
              not yet expired should be donated. Food safety must
              be checked by a human.
            </p>
          </div>
        </div>

        <form
          className="form-grid"
          onSubmit={event => {
            event.preventDefault();

            perform(async () => {
              const result = await post('/api/donations', {
                donation_id: 'DON_' + Date.now(),
                ...donation,
                quantity: Number(donation.quantity)
              });

              return result.message ||
                'Donation request created.';
            });
          }}
        >
          <label>
            Product
            <select
              required
              value={donation.product_id}
              onChange={e =>
                setDonation({
                  ...donation,
                  product_id: e.target.value
                })
              }
            >
              {inventoryOptions}
            </select>
          </label>

          <label>
            Quantity
            <input
              type="number"
              min="1"
              required
              value={donation.quantity}
              onChange={e =>
                setDonation({
                  ...donation,
                  quantity: e.target.value
                })
              }
            />
          </label>

          <label>
            Donation note
            <input
              value={donation.note}
              onChange={e =>
                setDonation({
                  ...donation,
                  note: e.target.value
                })
              }
            />
          </label>

          <div className="form-actions">
            <button
              className="primary-button"
              type="submit"
            >
              ＋ Create donation request
            </button>
          </div>
        </form>
      </Panel>

      <Panel
        title="Donation records"
        subtitle={`${donations.length} donation requests recorded`}
      >
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>DONATION ID</th>
                <th>PRODUCT</th>
                <th>QUANTITY</th>
                <th>STATUS</th>
                <th>NGO PARTNER</th>
                <th>CREATED</th>
                <th>ACTION</th>
              </tr>
            </thead>

            <tbody>
              {donations.length ? (
                donations.map(item => (
                  <tr key={item.donation_id}>
                    <td>{item.donation_id}</td>
                    <td>{item.product_name}</td>
                    <td>{item.quantity}</td>
                    <td>
                      <Badge value={item.status} />
                    </td>
                    <td>{item.ngo_name || 'Not matched'}</td>
                    <td>
                      {item.created_at
                        ? String(item.created_at)
                            .slice(0, 19)
                            .replace('T', ' ')
                        : '—'}
                    </td>
                    <td>
                      {String(item.status).toLowerCase() === 'pending' ? (
                        <button
                          className="delete-button"
                          onClick={() => deleteDonation(item)}
                        >
                          Delete
                        </button>
                      ) : (
                        <span className="footnote">
                          Protected
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="7" className="empty-cell">
                    No donation records found yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel
        title="Our NGO partners"
        subtitle="Organizations available in the demonstration database."
      >
        <div className="ngo-grid">
          {ngos.map(ngo => (
            <article className="ngo-card" key={ngo.name}>
              <div className="ngo-icon">🤝</div>

              <div>
                <strong>{ngo.name}</strong>
                <span>{ngo.city}</span>
              </div>

              <p>
                Capacity: {ngo.capacity_units} units
              </p>

              <Badge value={ngo.active ? 'Active' : 'Inactive'} />
            </article>
          ))}

          {!ngos.length && (
            <div className="empty-state">
              NGO partners will appear here.
            </div>
          )}
        </div>
      </Panel>
    </>
  );

  const renderAnalytics = () => (
    <>
      <div className="section-heading">
        <div>
          <span className="section-kicker">
            MEASURE YOUR IMPACT
          </span>

          <h2>Food rescue analytics</h2>
        </div>

        <span className="soft-label">
          Live database figures
        </span>
      </div>

      <div className="stats-grid">
        <StatCard
          label="Products tracked"
          value={summary.products}
          helper="Catalog size"
          icon="📦"
        />

        <StatCard
          label="Potential surplus"
          value={summary.surplus_units}
          helper="Current estimate"
          icon="🥕"
          tone="yellow"
        />

        <StatCard
          label="Redistributed units"
          value={summary.redistributed_units}
          helper="Accepted or later"
          icon="💚"
          tone="blue"
        />

        <StatCard
          label="At-risk products"
          value={summary.at_risk_products}
          helper="Requires review"
          icon="⏳"
          tone="pink"
        />
      </div>

      <Panel
        title="Daily sales performance"
        subtitle="Sales units recorded from committed processing batches."
      >
        <div className="chart-container">
          {daily.length ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={daily}
                margin={{
                  top: 12,
                  right: 12,
                  left: -16,
                  bottom: 4
                }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  vertical={false}
                  stroke="#edf2ef"
                />

                <XAxis
                  dataKey="aggregate_date"
                  tick={{
                    fill: '#82918a',
                    fontSize: 13
                  }}
                  axisLine={false}
                  tickLine={false}
                />

                <YAxis
                  tick={{
                    fill: '#82918a',
                    fontSize: 13
                  }}
                  axisLine={false}
                  tickLine={false}
                />

                <Tooltip />

                <Bar
                  dataKey="sales_units"
                  name="Sales units"
                  fill="#65a96c"
                  radius={[8, 8, 0, 0]}
                  maxBarSize={48}
                />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state">
              <span>📈</span>
              <strong>No sales data yet</strong>

              <p>
                Record a sale or generate synthetic events
                to populate analytics.
              </p>
            </div>
          )}
        </div>
      </Panel>

      <section className="impact-banner">
        <div className="impact-leaf">🌿</div>

        <div>
          <span>FOODRESCUE IMPACT</span>
          <h2>Make every product count.</h2>

          <p>
            Track surplus, review expiry risk and coordinate
            food redistribution.
          </p>
        </div>
      </section>
    </>
  );

  const renderPipeline = () => (
    <>
      <div className="section-heading">
        <div>
          <span className="section-kicker">
            DATA QUALITY & MONITORING
          </span>

          <h2>Pipeline monitor</h2>
        </div>

        <span className="soft-label">
          Processing overview
        </span>
      </div>

      <div className="stats-grid">
        <StatCard
          label="Raw events"
          value={quality.raw_events}
          helper="Persisted source events"
          icon="📥"
          tone="blue"
        />

        <StatCard
          label="Processed events"
          value={quality.processed_events}
          helper="Accepted unique events"
          icon="✅"
        />

        <StatCard
          label="Rejected events"
          value={quality.rejected_events}
          helper="Quarantined records"
          icon="⚠️"
          tone="pink"
        />

        <StatCard
          label="Pipeline runs"
          value={runs.length}
          helper="Recorded processing runs"
          icon="🔄"
          tone="yellow"
        />
      </div>

      <Panel
        title="Generate synthetic events"
        subtitle="Create reproducible sales micro-batches and submit them to the API."
      >
        <div className="generator-card">
          <div className="generator-icon">🔄</div>

          <div>
            <strong>Run the event generator</strong>

            <p>
              Open a terminal in the backend folder and execute:
            </p>

            <code>
              python generator/generate_events.py --count 100 --batch-size 25
            </code>
          </div>
        </div>

        <div className="checkpoint-box">
          <span>LAST COMMITTED BATCH</span>

          <strong>
            {quality.checkpoint?.last_batch_id ||
              'No checkpoint yet'}
          </strong>
        </div>
      </Panel>

      <Panel
        title="Processing history"
        subtitle="Recent batch execution and data-quality results."
      >
        <DataTable
          columns={[
            'RUN ID',
            'BATCH ID',
            'STATUS',
            'RECEIVED',
            'PROCESSED',
            'DUPLICATES',
            'REJECTED',
            'LATE'
          ]}
          rows={runs.map(run => [
            run.run_id,
            run.batch_id,
            <Badge value={run.status} />,
            run.received,
            run.processed,
            run.duplicates,
            run.rejected,
            run.late_events
          ])}
        />
      </Panel>
    </>
  );

  const pageContent = {
    Overview: renderOverview,
    Inventory: renderInventory,
    Predictions: renderPredictions,
    Donations: renderDonations,
    Analytics: renderAnalytics,
    'Pipeline Monitor': renderPipeline
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">🌿</div>

          <div className="brand-copy">
            <strong>FoodRescue</strong>
            <span>FRESH FOOD INTELLIGENCE</span>
          </div>
        </div>

        <div className="sidebar-caption">
          WORKSPACE
        </div>

        <nav className="navigation">
          {nav.map(item => (
            <button
              key={item.name}
              className={`nav-item ${
                page === item.name ? 'selected' : ''
              }`}
              onClick={() => changePage(item.name)}
            >
              <span className="nav-icon">
                {item.icon}
              </span>

              <span>{item.name}</span>

              {page === item.name && (
                <span className="active-marker" />
              )}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="sidebar-promo">
            <div>🍃</div>
            <strong>Save food. Share goodness.</strong>
            <p>
              Every rescued item makes a difference.
            </p>
          </div>

          <div className="connection-card">
            <span
              className={`connection-dot ${
                error ? 'offline' : ''
              }`}
            />

            <div>
              <strong>System status</strong>

              <small>
                {error ? 'Connection issue' : 'Monitoring API'}
              </small>
            </div>
          </div>

          <div className="sidebar-version">
            FoodRescue Prototype · v1.0
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumb">
            FOODRESCUE <span>/</span> {page.toUpperCase()}
          </div>

          <div className="topbar-actions">
            <div className="live-indicator">
              <span /> LIVE MONITORING
            </div>

            <button
              className="refresh-button"
              onClick={() => refresh(true)}
              disabled={loading}
            >
              ↻ {loading ? 'Loading' : 'Refresh'}
            </button>

            <div className="user-profile">
              <div className="user-avatar">FM</div>

              <div>
                <strong>FreshMart</strong>
                <small>Store admin</small>
              </div>
            </div>
          </div>
        </header>

        <div className="page-heading">
          <div>
            <div className="eyebrow">
              FRESHMART DEMO STORE · BELAGAVI
            </div>

            <h1>{page}</h1>
            <p>{pageDescriptions[page]}</p>
          </div>

          <div className="updated-label">
            {lastUpdated
              ? `Updated ${lastUpdated.toLocaleTimeString('en-IN', {
                  hour: '2-digit',
                  minute: '2-digit'
                })}`
              : 'Waiting for API data'}
          </div>
        </div>

        {error && (
          <div className="alert alert-error">
            <span>!</span>

            <div>
              <strong>Backend connection issue</strong>
              <p>{error}</p>
            </div>

            <button onClick={() => setError('')}>
              ×
            </button>
          </div>
        )}

        {notice && (
          <div className="alert alert-success">
            <span>✓</span>
            <p>{notice}</p>

            <button onClick={() => setNotice('')}>
              ×
            </button>
          </div>
        )}

        {loading && !lastUpdated ? (
          <div className="loading-state">
            <div className="loader" />
            <span>Gathering fresh data…</span>
          </div>
        ) : (
          pageContent[page]()
        )}

        <footer className="app-footer">
          <span>
            🌱 FoodRescue · Food Waste Intelligence & Redistribution
          </span>

          <span>
            Prototype data · Human food-safety verification required
          </span>
        </footer>
      </main>
    </div>
  );
}

export default App;
