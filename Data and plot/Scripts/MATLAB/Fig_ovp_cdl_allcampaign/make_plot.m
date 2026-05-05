% ========== MATLAB Figure Template ==========

SCRIPT_DIR = fileparts(mfilename('fullpath'));
PROJECT_ROOT = fullfile(SCRIPT_DIR, '..', '..', '..');
addpath(fullfile(PROJECT_ROOT, 'Scripts', 'MATLAB'));
addpath(fullfile(PROJECT_ROOT, 'Scripts', 'MATLAB', 'utils'));

disp("Using registry from: " + which('registry'));

% Load metadata
m = metadata();

% OUTPUT DIRECTORY ROOT
OUTPUT_DIR_ROOT = fullfile(SCRIPT_DIR, '..', '..', '..', 'Figures_SI', m.stable_id);
if ~exist(OUTPUT_DIR_ROOT, 'dir')
    mkdir(OUTPUT_DIR_ROOT);
end

%% ===== Load Data =====
data = readtable(get_data(m.data_keys(1)), 'VariableNamingRule', 'preserve');
data = data(:,{'Experiment', 'Overpotential @ 50 mA','Cdl mF cm-2'});

Overpotential = data{:, 'Overpotential @ 50 mA'};
ECSA         = data{:, 'Cdl mF cm-2'};
Experiments  = string(data{:, 'Experiment'});

%% ===== Step 0: Get row index of key experiments =====
idx_584 = getExpIndex(data, "exp584");

idx_610  = getExpIndex(data, "exp610");
idx_728  = getExpIndex(data, "exp728");

idx_729  = getExpIndex(data, "exp729");
idx_858  = getExpIndex(data, "exp858");

idx_859  = getExpIndex(data, "exp859");
idx_978  = getExpIndex(data, "exp978");

idx_979  = getExpIndex(data, "exp979");
idx_1098 = getExpIndex(data, "exp1098");

idx_1099 = getExpIndex(data, "exp1099");
idx_1258 = getExpIndex(data, "exp1258");

n = height(data);
rows = (1:n)';

mask_typeI = rows <= idx_584;

mask_c1 = rows >= idx_610  & rows <= idx_728;
mask_c2 = rows >= idx_729  & rows <= idx_858;
mask_c3 = rows >= idx_859  & rows <= idx_978;
mask_c4 = rows >= idx_979  & rows <= idx_1098;
mask_c5 = rows >= idx_1099 & rows <= idx_1258;

all_masks = {mask_c1, mask_c2, mask_c3, mask_c4, mask_c5};

%% ===== Step 2: apply valid filter =====
valid_idx = ~isnan(Overpotential) & ~isnan(ECSA) & ECSA > 0;

Overpotential = Overpotential(valid_idx);
ECSA         = ECSA(valid_idx);
Experiments  = Experiments(valid_idx);

mask_typeI = mask_typeI(valid_idx);
for k = 1:5
    all_masks{k} = all_masks{k}(valid_idx);
end

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


for k = 1:5

    fprintf("Rendering Campaign %d...\n", k);

    OUTPUT_DIR = fullfile(OUTPUT_DIR_ROOT, sprintf("Campaign_%d", k));
    if ~exist(OUTPUT_DIR, "dir")
        mkdir(OUTPUT_DIR);
    end

    mask_k = all_masks{k};
    idx_list = find(mask_k);

    if isempty(idx_list)
        warning("Campaign %d has NO points. Skipping...", k);
        continue;
    end

    %% ===== Create figure =====
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

    %% ===== Gradient for this Campaign =====
    n_pts = numel(idx_list);
    [cmap, alphaList] = generateGradient_LightToDeep(deep_colors{k}, n_pts);

    for ii = 1:n_pts
        i = idx_list(ii);
        scatter(log_ECSA(i), Overpotential(i), ...
            26, cmap(ii,:), 'filled', ...
            'MarkerFaceAlpha', alphaList(ii), ...
            'MarkerEdgeColor', cmap(ii,:), ...
            'MarkerEdgeAlpha', alphaList(ii)*0.6);
    end

    % Legend entry (single deep color)
    scatter(nan, nan, 35, cmap(end,:), 'filled', ...
        'DisplayName', sprintf("Campaign %d", k));
    
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
    base = fullfile(OUTPUT_DIR, sprintf("%s_C%d", m.stable_id, k));
    exportgraphics(f, base + ".png", 'Resolution', 600);
    exportgraphics(f, base + ".eps", 'ContentType', 'vector');

end


% =====================================================
% ====================== FUNCTIONS =====================
% =====================================================

function m = metadata()
    m.stable_id = "Fig_ovp_cdl_allcampaign";
    m.script = mfilename('fullpath');
    m.data_keys = ["All_Ovp_Cdl"];
    m.figure_type = "SI";
end

function [cmap, alphaList] = generateGradient_LightToDeep(hexColor, n)

    if n <= 0
        cmap = [];
        alphaList = [];
        return
    end

    if isstring(hexColor)
        hexColor = char(hexColor);
    end

    deepRGB = sscanf(hexColor(2:end), '%02x%02x%02x')' / 255;
    lightRGB = deepRGB + (1 - deepRGB)*0.70;

    cmap = zeros(n,3);
    for kk = 1:3
        cmap(:,kk) = linspace(lightRGB(kk), deepRGB(kk), n);
    end

    alphaList = linspace(0.30, 0.85, n)';
end