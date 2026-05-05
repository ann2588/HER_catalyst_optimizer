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

parentFolder = OUTPUT_DIR_ROOT;
dataFile = get_data(m.data_keys(1));

processFoldersAndPlotData(parentFolder, dataFile, 15);

function processFoldersAndPlotData(parentFolder, dataFile, zColumn, polygonVertices)

    % Load the file inside the folder 
    if isempty(dataFile)
        warning('No files found in folder %s', folderName);
    end

    % Load data from the specified file
    % Assuming one file per folder; load it
    data = readtable(dataFile, 'VariableNamingRule', 'preserve');
    data = data(:, {'Experiment', 'Cu', 'Cr', 'Se', 'V', 'Mg', 'S', 'Fe', 'Co', 'Ni', 'P', ...
    'blank', 'Volt', 'Time', 'Cdl mF cm-2'});

    if nargin < 4
        polygonVertices = 10;
    end
    
    endding = getExpIndex(data, 'exp584'); % ending for pretrain
    
    % Define vertices of the polygon
    theta = linspace(0, 2 * pi, polygonVertices + 1); % Include endpoint for closure
    polygon_x = cos(theta(1:end-1)); % X-coordinates of vertices
    polygon_y = sin(theta(1:end-1)); % Y-coordinates of vertices
    vertices = [polygon_x', polygon_y']; % Vertices matrix
    elements = {'Cu', 'Cr', 'Se', 'V', 'Mg', 'S', 'Fe', 'Co', 'Ni', 'P'}; % Element names
    major_elements = {'S', 'P', 'Se'}; % Solid black line elements

    % Extract relevant columns
    original_weights = table2array(data(:, 2:11)); % Columns B to K
    z_values = table2array(data(:, zColumn)); % Z-values for visualization
    z_values = log10(z_values);

    % Normalize weights for visualization
    weights = original_weights ./ 70; % Scale weights by dividing by 70
    weights = weights ./ sum(weights, 2); % Normalize rows to sum to 1

    % Compute Cartesian coordinates for each point
    cartesian_coords = weights * vertices; % Linear combination using weights
    x_coords = cartesian_coords(:, 1); % X-coordinates
    y_coords = cartesian_coords(:, 2); % Y-coordinates


    % Create a 2D scatter plot
    figure('Units', 'inches', 'Position', [1, 1, 6, 4.8], 'Resize', 'off', 'Color', 'w');
    hold on;

    % Draw radial axes
    for j = 1:polygonVertices
        if ismember(elements{j}, major_elements)
            quiver(0, 0, cos(theta(j)), sin(theta(j)), 1, 'Color', 'k', ...
                'LineWidth', 0.75, 'MaxHeadSize', 0.2);
        else
            quiver(0, 0, cos(theta(j)), sin(theta(j)), 1, 'Color', [0.5, 0.5, 0.5], ...
                'LineWidth', 0.75, 'LineStyle', '--', 'MaxHeadSize', 0.2);
        end
    end

    % Label each radial axis
    for j = 1:polygonVertices
        text(1.1 * cos(theta(j)), 1.1 * sin(theta(j)), elements{j}, ...
            'FontSize', 12, 'FontWeight', 'bold', ...
            'HorizontalAlignment', 'center', 'VerticalAlignment', 'middle');
    end
    start = 1;
    % Scatter plot with color mapped to Z-values
    s = scatter(x_coords(start:endding), y_coords(start:endding), 50, z_values(start:endding), 'filled', 'MarkerFaceAlpha', 0.85);
    s.MarkerFaceAlpha = 1; 
    s.MarkerEdgeAlpha = 1;
    s.MarkerEdgeColor = [0.85, 0.85 ,0.85]; % Neutral gray (50% intensity)
    s.LineWidth = 0.5; % Set marker edge thickness to 0.5 pt

   
    %caxis([-1, 0]); % Set the color bar limits
    c = colorbar;
    configureColorBar(c, sprintf('log Cdl (mF cm-2)')); % Font sizes in point
    colormap(flipud(gray));
    c.Position = [5.15, 0.2, 0.2, (4.8-0.3)];

    ax = gca;
    ax.Position = [0.05, 0.11, 0.7750, 0.8150];

    hold on; % Keep adding elements to the plot

    % Set aesthetics
    axis equal;
    axis off;
    grid off;

    
    % Save the figure
    set(gcf, 'Color', 'w'); % 'w' specifies white background
    baseName = "ecsa_pretrain";
    filename = sprintf('%s.eps', baseName);
    saveFilePath = fullfile(parentFolder, filename);
    exportgraphics(gcf, saveFilePath, 'ContentType', 'vector');

end


% =====================================================

function m = metadata()
    m.stable_id = "Fig_landscape_ecsa";
    m.script = mfilename('fullpath');
    m.data_keys = ["All_Ovp_Cdl_Tafel"];
    m.figure_type = "SI";
end

function configureColorBar(cbar, labelText, labelFontSize, tickFontSize)
    % CONFIGURECOLORBAR Customizes the color bar properties
    %
    % Inputs:
    %   cbar - Color bar handle
    %   labelText - String for the color bar label
    %   labelFontSize - Font size for the label (default: 12)
    %   tickFontSize - Font size for the tick labels (default: 8)
    %
    % Example:
    %   c = colorbar;
    %   configureColorBar(c, 'Z-Values', 14, 10);

    % Check for optional arguments and set defaults
    if nargin < 3 || isempty(labelFontSize)
        labelFontSize = 20; % Default font size for the label
    end
    if nargin < 4 || isempty(tickFontSize)
        tickFontSize = 12; % Default font size for the tick labels
    end

    cbar.Units = 'Inches';
    cbar.Label.String = labelText;
    cbar.Label.FontSize = labelFontSize;
    cbar.Label.FontWeight = 'bold'; % Optional: Make label bold
    cbar.Label.FontName = 'Arial'; % Set the font type for the label

    % Set the tick label font size
    cbar.FontSize = tickFontSize; % Set font size for tick labels
    cbar.FontName = 'Arial'; % Ensure tick font matches label

    % Remove the color bar frame
    cbar.Box = 'off';

end

function rgb = hex2rgb(hex)
    hex = char(hex);
    if hex(1) == '#'
        hex = hex(2:end);
    end
    if numel(hex) ~= 6
        error('hex code must be 6 characters.');
    end
    r = hex2dec(hex(1:2));
    g = hex2dec(hex(3:4));
    b = hex2dec(hex(5:6));
    rgb = [r g b] / 255;
end