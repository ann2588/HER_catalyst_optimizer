% ========== MATLAB Figure Template ==========

SCRIPT_DIR = fileparts(mfilename('fullpath'));
PROJECT_ROOT = fullfile(SCRIPT_DIR, '..', '..', '..');
addpath(fullfile(PROJECT_ROOT, 'Scripts', 'MATLAB'));
addpath(fullfile(PROJECT_ROOT, 'Scripts', 'MATLAB', 'utils'));

disp("Using registry from: " + which('registry'));

% Load metadata
m = metadata();

% OUTPUT DIRECTORY ROOT
OUTPUT_DIR_ROOT = fullfile(SCRIPT_DIR, '..', '..', '..', 'Figures_Main', m.stable_id);
if ~exist(OUTPUT_DIR_ROOT, 'dir')
    mkdir(OUTPUT_DIR_ROOT);
end

%% ===== Load Data =====
data = readtable(get_data(m.data_keys(1)), 'VariableNamingRule', 'preserve');
data = data(:,{'Experiment', 'Overpotential @ 50 mA','Cdl mF cm-2'});

Overpotential = data{:, 'Overpotential @ 50 mA'};
ECSA         = data{:, 'Cdl mF cm-2'};
Experiments  = string(data{:, 'Experiment'});


%% ===== Step 2: apply valid filter =====
valid_idx = ~isnan(Overpotential) & ~isnan(ECSA) & ECSA > 0;

Overpotential = Overpotential(valid_idx);
ECSA         = ECSA(valid_idx);
Experiments  = Experiments(valid_idx);



n = height(data);
rows = (1:n)';
idx_584 = getExpIndex(data, "exp584");
mask_typeI = rows <= idx_584;
mask_typeI = mask_typeI(valid_idx);

log_ECSA = log10(ECSA);

%% ===== Deep Colors for the 5 campaigns =====
deep_colors = {
    '#2F3E75'   % Campaign 1 
    '#D98E4A'   % Campaign 2 
    '#567C55'   % Campaign 3 
    '#B44A3F'   % Campaign 4 
    '#888888'   % Low-seed 
};

%% ===== Global Axis Limits =====
X_MIN = -1.5;
X_MAX =  2.5;

Y_MIN = -1.0;
Y_MAX =  0.0;

%% ============================================================
%       Pretrained only
%% ============================================================
fprintf("Pretrained Data");

OUTPUT_DIR = fullfile(OUTPUT_DIR_ROOT, sprintf("Pretrained"));
if ~exist(OUTPUT_DIR, "dir")
    mkdir(OUTPUT_DIR);
end

idx_list = find(mask_typeI);

f = figure('Units','inches','Position',[1,1,3.6,3.6]);
f.Resize = "off";
hold on;

%% ===== Plot Pretrained =====
scatter(log_ECSA(mask_typeI), Overpotential(mask_typeI), ...
    22, 'filled', ...
    'MarkerFaceColor', "#697EC4", ...
    'MarkerEdgeColor', [0.8 0.8 0.8], ...
    'MarkerFaceAlpha', 0.3, ...
    'DisplayName','Pretrained');

xlabel('log_{10} C_{dl} (mF/cm^2)');
ylabel('\eta_{50}');

%% ===== Apply unified axis limits =====
xlim([X_MIN, X_MAX]);
ylim([Y_MIN, Y_MAX]);

ax = gca;
ax.Box = 'on';     
ax.LineWidth = 0.5;  
ax.XColor = 'k';         
ax.YColor = 'k'; 


grid off;
hold off;

%% ===== Save =====
base = fullfile(OUTPUT_DIR, m.stable_id);
exportgraphics(f, base + ".png", 'Resolution', 600);
exportgraphics(f, base + ".eps", 'ContentType', 'vector');

% =====================================================
% ====================== FUNCTIONS =====================
% =====================================================

function m = metadata()
    m.stable_id = "Fig_ovp_cdl_pretrained";
    m.script = mfilename('fullpath');
    m.data_keys = ["Pretrain_Ovp_Cdl"];
    m.figure_type = "Main";
end