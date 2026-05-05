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
dataName = {'global', 'local'};
parentFolder = OUTPUT_DIR_ROOT;

% ========== Start plotting ==========
% Load the data
for z = 1:numel(dataName)
    data = readtable(get_data(m.data_keys(z)), 'VariableNamingRule', 'preserve');
    data = data(:,{'Unnamed: 0','Cu', 'Cr', 'Se', 'V', 'Mg', 'S', 'Fe', 'Co', 'Ni', 'P','blank','Volt','Time', 'Overpotential V at 50.0 mA/cm2'});
    % Define the data names and corresponding columns
    datanames = {'Overpotential'};
    z_columns = [15];

    % Define vertices of the 10-sided polygon
    n = 10;
    theta = linspace(0, 2 * pi, n + 1); % Include endpoint for closure
    polygon_x = cos(theta(1:end-1)); % X-coordinates of vertices
    polygon_y = sin(theta(1:end-1)); % Y-coordinates of vertices
    vertices = [polygon_x', polygon_y']; % n x 2 matrix of polygon vertices
    elements = {'Cu', 'Cr', 'Se', 'V', 'Mg', 'S', 'Fe', 'Co', 'Ni', 'P'}; % Element names
    % Define solid black line elements
    major_elements = {'S', 'P', 'Se'};

    % Loop through each dataname and z_column
    for i = 1:length(datanames)
        dataname = datanames{i};  % Get the current dataname
        z_column = z_columns(i);  % Get the corresponding column

        % Extract relevant columns
        original_weights = table2array(data(:, 2:11)); % Columns B to K (original composition values)
        z_values = table2array(data(:, z_column)); % Current Z-values for color representation
        
        % Normalize weights for visualization
        weights = original_weights ./ 70; % Scale weights by dividing by 70
        weights = weights ./ sum(weights, 2); % Normalize rows to sum to 1

        % Compute Cartesian coordinates for each point
        cartesian_coords = weights * vertices; % Linear combination using weights
        x_coords = cartesian_coords(:, 1); % X-coordinates
        y_coords = cartesian_coords(:, 2); % Y-coordinates

        % Create a 2D scatter plot
        f = figure('Units', 'inches', 'Position', [1, 1, 6, 4.8]); % 4.8x4.8 inches
        f.Resize = 'off';

        hold on;

        % Define the radial axes
        for j = 1:n
            % Set arrow style based on element type
            if ismember(elements{j}, major_elements)
                % Solid black arrow for S, P, Se
                quiver(0, 0, cos(theta(j)), sin(theta(j)), 1, 'Color', 'k', 'LineWidth', 1.5, 'MaxHeadSize', 0.2);
            else
                % Dashed gray arrow for other elements
                quiver(0, 0, cos(theta(j)), sin(theta(j)), 1, 'Color', [0.5, 0.5, 0.5], 'LineWidth', 1, 'LineStyle', '--', 'MaxHeadSize', 0.2);
            end
        end

        % Label each radial axis
        for j = 1:n
            text(1.1 * cos(theta(j)), 1.1 * sin(theta(j)), elements{j}, ...
                'FontSize', 12, 'FontWeight', 'bold', ...
                'HorizontalAlignment', 'center', 'VerticalAlignment', 'middle');
        end

        % Scatter Plot, pretrain
        start = 1;
        endding = 593;
        s = scatter(x_coords(start:endding), y_coords(start:endding), 50, z_values(start:endding), 'filled'); % Data points with color representing Z-values
        s.MarkerFaceAlpha = 1; 
        s.MarkerEdgeAlpha = 1;
        s.MarkerEdgeColor = [0.85, 0.85 ,0.85]; % Neutral gray (50% intensity)
        s.LineWidth = 0.5; % Set marker edge thickness to 0.5 pt
        
        % point from model
        s_bandit = scatter(x_coords(endding:end), y_coords(endding:end), 100, hex2rgb("#C86496"), 'filled' ,'Marker', 's'); 
        s_bandit.MarkerFaceAlpha = 1; 
        s_bandit.MarkerEdgeAlpha = 1;
        s_bandit.MarkerEdgeColor = [0.85, 0.85 ,0.85]; % Neutral gray (50% intensity

        s_bandit.LineWidth = 0.5; % Set marker edge thickness to 0.5 pt


        % starting point (random pick for demo)
        s_371 = scatter(x_coords(371), y_coords(371), 50, 'k', 'MarkerFaceColor', 'k', 'Marker', 'd');

        % Set color bar and configure
        clim([-1, 0]); % Set the color bar limits
        c = colorbar;
        configureColorBar(c, sprintf('%s (@ 50 mA cm^{-2})', dataname)); % Font sizes in point
        colormap(flipud(gray));
        c.Position = [5.15, 0.2, 0.2, (4.8-0.3)];
        

        ax = gca;
        ax.Position = [0.05, 0.11, 0.7750, 0.8150];

        % Set aesthetics
        axis equal;
        axis off;
        grid on;


        %title(sprintf('2D Distribution of %s', dataname), 'FontSize',14, 'Units', 'normalized', 'Position', [0.5, 1.1]);
        
        dcm = datacursormode;
        set(dcm, 'UpdateFcn', @(obj, event_obj) data_tip_callback(event_obj, original_weights, z_values, elements));
        datacursormode on

        % Save the plot
        set(gcf, 'Color', 'w'); % 'w' specifies white background
        filename = fullfile(OUTPUT_DIR_ROOT, sprintf('%s.eps', dataName{z}));
        exportgraphics(gcf, filename, 'ContentType', 'vector'); % Save as eps
        filename = fullfile(OUTPUT_DIR_ROOT, sprintf('%s.png', dataName{z}));
        exportgraphics(gcf, filename, 'Resolution', 600); % Save as PNG
        hold off;
    end
end

function cmap = rpb
    % RED_PURPLE_BLUE colormap: Gradient from Red to Purple to Blue
    % Define the number of colors
    n = 256; % Adjust as needed for smoother gradients

    % Create the red-to-purple gradient
    half_n = floor(n / 2);
    r = [linspace(1, 1, half_n), linspace(1, 0, half_n)]; % Red component
    g = [linspace(0, 0.5, half_n), linspace(0.5, 0, half_n)]; % Green component for purple
    b = [linspace(0, 1, half_n), ones(1, half_n)]; % Blue component

    % Combine into RGB matrix
    cmap = [r', g', b'];
end

function cmap = seismic
    % SEISMIC colormap: Red-White-Blue colormap
    n = 256; % Total number of colors
    half_n = floor(n / 2);
    r = [linspace(0, 1, half_n), ones(1, half_n)];
    g = [linspace(0, 1, half_n), linspace(1, 0, half_n)];
    b = [ones(1, half_n), linspace(1, 0, half_n)];
    cmap = [r', g', b']; % Combine into RGB matrix
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


% =====================================================
function m = metadata()
    m.stable_id = "Fig_landscape_bandit";
    m.script = mfilename('fullpath');
    m.data_keys = ["bandit_insilico_global", "bandit_insilico_local"];
    m.figure_type = "Main";
end
